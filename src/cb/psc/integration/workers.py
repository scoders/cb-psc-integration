import logging
import os.path
import importlib.util
import sys

import redis as r
from rq import Worker, Queue, Connection
from rq.job import Job
from rq.registry import StartedJobRegistry
import requests

import cbapi.psc.threathunter as cbth

from cb.psc.integration.config import config
from cb.psc.integration.database import session, Binary
import cb.psc.integration.connector as connector

logging.basicConfig()
log = logging.getLogger()
log.setLevel(config.loglevel)

listen = ["binary_retrieval", "binary_analysis", "binary_cleanup"]

redis = r.Redis(host=config.redis_host, port=config.redis_port)
binary_retrieval = Queue("binary_retrieval", connection=redis)
binary_analysis = Queue("binary_analysis", connection=redis)
binary_cleanup = Queue("binary_cleanup", connection=redis)

log = logging.getLogger(__name__)
log.setLevel(config.loglevel)

cb = cbth.CbThreatHunterAPI(profile=config.cbth_profile)


def download_binary(hash, url):
    """
    Downloads the binary with the given hash from the given (UBS-supplied) URL.
    """
    log.info(f"downloading binary {hash} from {url}")
    resp = requests.get(url, stream=True, timeout=config.binary_timeout)

    # TODO(ww): Support re-trying the download?
    if not resp.status_code == requests.codes.ok:
        log.error(f"download failed for {hash}: {resp.status_code}")
        resp.raise_for_status()

    redis.set(f"/binaries/{hash}", resp.raw.read())

    binary = Binary.from_hash(hash)
    if binary is None:
        Binary.create(sha256=hash, available=True)
    else:
        binary.update(available=True)


# TODO(ww): Probably belongs in another file
def filter_available(hashes):
    """
    Given a list of hashes, returns the ones that are currently
    available within the binary cache.
    """
    results = (
        session.query(Binary.sha256)
        .filter((Binary.sha256.in_(hashes)) & (Binary.available))
        .all()
    )

    # TODO(ww): This is a little silly. Is there a right
    # way to get just a list, and not a list of tuples,
    # from an SQLAlchemy filter?
    available_hashes = [r for r, in results]

    log.debug(f"available hashes: {available_hashes}")

    return list(set(hashes) - set(available_hashes))


def fetch_binaries(hashes):
    """
    Attempts to retrieve and analyze each of binaries corresponding
    to the given hashes.
    """
    log.debug(f"fetch_binaries: {len(hashes)} hashes")
    hashes = filter_available(hashes)

    if len(hashes) == 0:
        log.info("no hashes that aren't already available")
        return

    # NOTE(ww): Binary retrieval happens in two stages:
    #  * We retrieve a list of available/unavailable binaries and their
    #    URLs from the PSC UBS API.
    #  * We enqueue each available binary for downloading + caching in redis.
    try:
        downloads = cb.select(cbth.Downloads, hashes)
    except Exception as e:  # noqa
        log.error(f"cbth responded with an error: {e}")
        return

    for found in downloads.found:
        download = binary_retrieval.enqueue(download_binary, found.sha256, found.url)
        binary_analysis.enqueue(analyze_binary, found.sha256, depends_on=download)

    if len(downloads.error) > 0:
        log.info(f"retrying retrieval of {len(downloads.error)}/{len(hashes)} binaries")
        binary_retrieval.enqueue(fetch_binaries, downloads.error)

    if len(downloads.not_found) > 0:
        log.warning(f"no binaries found for hashes: {','.join(downloads.not_found)}")


def active_analyses():
    """
    Returns a list of job IDs corresponding to active (pending or running)
    analysis tasks.
    """
    # TODO(ww): Use this once fetch_many makes it into an rq release.
    # jobs = Job.fetch_many(binary_analysis.job_ids, connection=redis)
    pending_jobs = [Job.fetch(job_id) for job_id in binary_analysis.job_ids]

    pending_ids = [job.id for job in pending_jobs if job.func_name != "analyze_binary"]
    started = StartedJobRegistry("binary_analysis", connection=redis)

    return pending_ids + started.get_job_ids()


def analyze_binary(hash):
    """
    Enqueues the binary corresponding to the given hash for analysis by all connectors.
    """
    log.debug(f"analyzing binary: {hash}")

    binary = Binary.from_hash(hash)
    redis.set(binary.count_key, len(list(connector.connectors())))

    for conn in connector.connectors():
        log.debug(f"running {conn.name} analysis")
        binary_analysis.enqueue(conn._analyze, binary)


def flush_binary(binary):
    """
    Flushes the binary corresponding to the given hash from the binary cache.
    """
    log.debug(f"flush_binary: {binary.sha256}")

    refcount = int(redis.get(binary.count_key))

    if refcount > 0:
        log.info(f"binary {binary.sha256} has {refcount} references remaining")
        return

    log.info(f"flushing {binary.sha256} from redis")
    redis.delete(binary.data_key, binary.count_key)

    binary.update(available=False)


def load_connectors():
    """
    Loads all connectors from all configured connector directories.
    """
    log.debug("loading connectors")
    for path in config.connector_dirs:
        if not os.path.isdir(path):
            log.warning(f"{path} is not a directory, skipping")
            continue

        log.info(f"searching path: {path}")
        for conn_dir in os.scandir(path):
            if not conn_dir.is_dir():
                log.debug(f"{conn_dir.path} is not a directory, skipping")
                continue

            conn_file = os.path.join(conn_dir.path, "connector.py")
            if not os.path.isfile(conn_file):
                log.warning(f"{conn_file} does not exist, skipping")
                continue

            mod_name = f"connectors.{conn_dir.name}"
            log.info(f"loading {conn_file} as {mod_name}")
            try:
                spec = importlib.util.spec_from_file_location(mod_name, conn_file)
                conn_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(conn_mod)

                # Gross. But apparently the "correct" way to get
                # dynamically loaded modules to work with Pickle.
                sys.modules[mod_name] = conn_mod
            except Exception as e:
                log.error(f"failed to load {conn_file}: {e}")

    log.info(f"loaded connectors: {', '.join(c.name for c in connector.connectors())}")


if __name__ == "__main__":
    load_connectors()
    with Connection(redis):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
