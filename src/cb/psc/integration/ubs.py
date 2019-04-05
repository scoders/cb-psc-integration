import logging

import requests
from rq import Queue
import cbapi.psc.threathunter as cbth

from .config import config
from .connector import analyze_binary
from .database import session, Binary
from .workers import conn as redis

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

cb = cbth.CbThreatHunterAPI(profile=config.cbth_profile)

binary_retrieval = Queue("binary_retrieval", connection=redis)
binary_analysis = Queue("binary_analysis", connection=redis)


def download_binary(hash, url):
    log.info(f"downloading binary {hash} from {url}")
    # TODO(ww): Exception handling.
    resp = requests.get(url, stream=True, timeout=config.binary_timeout)
    redis.set(hash, resp.raw.read())

    Binary.create(sha256=hash, available=True)

    return None


def filter_available(hashes):
    results = session.query(Binary.sha256).filter(
        (Binary.sha256.in_(hashes)) & (Binary.available)
    ).all()

    # TODO(ww): This is a little silly. Is there a right
    # way to get just a list, and not a list of tuples,
    # from an SQLAlchemy filter?
    available_hashes = [r for r, in results]

    log.debug(f"available hashes: {available_hashes}")

    return list(set(hashes) - set(available_hashes))


def fetch_binaries(hashes):
    hashes = filter_available(hashes)

    if len(hashes) == 0:
        log.info("no new hashes that aren't already available")
        return None

    # NOTE(ww): Binary retrieval happens in two stages:
    #  * We retrieve a list of available/unavailable binaries and their
    #    URLs from the PSC UBS API.
    #  * We enqueue each available binary for downloading + caching in redis.
    downloads = cb.select(cbth.Downloads, hashes)

    for found in downloads.found:
        download = binary_retrieval.enqueue(download_binary, found.sha256, found.url)
        binary_analysis.enqueue(analyze_binary, found.sha256, depends_on=download)

    if len(downloads.error) > 0:
        log.info(f"retrying retrieval of {len(downloads.error)}/{len(hashes)} binaries")
        binary_retrieval.enqueue(fetch_binaries, downloads.error)

    if len(downloads.not_found) > 0:
        log.warning(f"no binaries found for hashes: {','.join(downloads.not_found)}")

    return None
