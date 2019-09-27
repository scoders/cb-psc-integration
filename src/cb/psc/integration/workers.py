import importlib.util
import logging
import os.path
import sys

import cbapi.psc.threathunter as threathunter
import redis as r
import requests
from cbapi.errors import ApiError
from rq import Connection, Queue, Worker
from rq.job import Job
from rq.registry import StartedJobRegistry

import cb.psc.integration.connector as connector
from cb.psc.integration.config import config
from cb.psc.integration.database import AnalysisResult, Binary, session
from cb.psc.integration.utils import cbth, grouper, timeout_handler

logging.basicConfig()
log = logging.getLogger()
log.setLevel(config.loglevel)

listen = ["binary_retrieval", "binary_analysis", "binary_cleanup", "result_dispatch"]

redis = r.Redis.from_url(config.redis_url)

binary_retrieval = Queue("binary_retrieval", connection=redis)
binary_analysis = Queue("binary_analysis", connection=redis)
binary_cleanup = Queue("binary_cleanup", connection=redis)
result_dispatch = Queue("result_dispatch", connection=redis)


log = logging.getLogger(__name__)
log.setLevel(config.loglevel)


def download_binary(hash, url, *, retry):
    """
    Downloads the binary with the given hash from the given (UBS-supplied) URL.
    """
    log.info(f"downloading binary {hash} from {url}")
    resp = requests.get(url, stream=True, timeout=config.binary_timeout)

    if not resp.status_code == requests.codes.ok:
        if resp.status_code == 404 and retry > 0:
            log.warning(f"download 404'd for {hash}, retrying ({retry - 1} remaining)")
            binary_retrieval.enqueue(download_binary, hash, url, retry=retry - 1)
        else:
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
        session.query(Binary.sha256).filter((Binary.sha256.in_(hashes)) & (Binary.available)).all()
    )

    # TODO(ww): This is a little silly. Is there a right
    # way to get just a list, and not a list of tuples,
    # from an SQLAlchemy filter?
    available_hashes = [r for r, in results]

    log.debug(f"available hashes: {available_hashes}")

    return list(set(hashes) - set(available_hashes))


def fetch_query(query, limit=None):
    """
    Attempts to retrieve and analyze each of the binaries corresponding
    to the given CbTH query.
    """
    log.debug(f"fetch_query: {query} (limit={limit})")

    try:
        processes = cbth().select(threathunter.Process).where(query)
        if limit is not None:
            processes = processes[0:limit]

        for proc_group in grouper(processes, 10):
            hashes = [p.process_sha256 for p in proc_group if p]
            binary_retrieval.enqueue(fetch_binaries, hashes)
    except Exception as e:  # noqa
        # TODO(ww): Log this.
        return


def fetch_binaries(hashes):
    """
    Attempts to retrieve and analyze each of the binaries corresponding
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
        downloads = cbth().select(threathunter.Downloads, hashes)
    except Exception as e:  # noqa
        log.error(f"CbTH responded with an error: {e}")
        return

    for found in downloads.found:
        download = binary_retrieval.enqueue(
            download_binary, found.sha256, found.url, retry=config.binary_fetch_max_retry
        )
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
    pending_jobs = Job.fetch_many(binary_analysis.job_ids, connection=redis)
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
        binary_analysis.enqueue(conn._analyze, binary, job_timeout=config.binary_timeout)


def flush_binary(binary):
    """
    Flushes the binary corresponding to the given hash from the binary cache.
    """
    log.debug(f"flush_binary: {binary.sha256}")
    redis.delete(binary.data_key, binary.count_key)
    binary.update(available=False)


def dispatch_to_feed(feed_id, results):
    log.debug(f"dispatch_to_feed: {feed_id}")

    try:
        feed = cbth().select(threathunter.Feed, feed_id)
    except ApiError as e:
        log.error(f"couldn't find CbTH feed {feed_id}: {e}")
        return

    reports = []
    for result in results:
        rep_dict = {
            "id": str(result.id),
            "timestamp": int(result.scan_time.timestamp()),
            "title": result.connector_name,
            "description": result.analysis_name,
            "severity": result.score,
            "iocs_v2": [ioc.as_dict() for ioc in result.iocs],
        }

        report = cbth().create(threathunter.Report, rep_dict)
        reports.append(report)

    feed.append_reports(reports)


def dispatch_to_watchlist(watchlist_id, results):
    log.debug(f"dispatch_to_watchlist: {watchlist_id}")
    log.warning("Watching dispatch is not yet implemented")
    # try:
    #     watchlist = cbth().select(threathunter.Watchlist, watchlist_id)
    # except ApiError as e:
    #     log.error(f"couldn't find CbTH watchlist {watchlist_id}: {e}")
    #     return


def dispatch_result(result_ids):
    """
    Dispatches the given results (by ID) to the appropriate sink.
    """
    log.debug(f"dispatch_result: {len(result_ids)} results")
    results = session.query(AnalysisResult).filter(AnalysisResult.id.in_(result_ids)).all()

    results = [result for result in results if not result.dispatched]
    if not results:
        return

    # all results come from the same analysis, hence same sink (one per conn)
    sink = config.sinks[results[0].connector_name]
    log.debug(f"dispatch_result: sending {len(results)} results to {sink}")

    if sink.kind == "feed":
        dispatch_to_feed(sink.id, results)
    elif sink.kind == "watchlist":
        dispatch_to_watchlist(sink.id, results)

    for result in results:
        result.update(dispatched=True)


def load_connectors():
    """
    Loads all connectors from all configured connector directories.
    """
    log.debug("loading connectors")
    for path in config.connector_dirs:
        if not os.path.isdir(path):
            log.warning(f"{path} is not a directory, skipping")
            continue
        if path not in sys.path:
            sys.path.append(path)

        log.info(f"searching path: {path}")
        for conn_dir in os.scandir(path):
            if not conn_dir.is_dir():
                log.debug(f"{conn_dir.path} is not a directory, skipping")
                continue

            conn_file = os.path.join(conn_dir.path, "connector.py")
            if not os.path.isfile(conn_file):
                log.warning(f"{conn_file} does not exist, skipping")
                continue

            if conn_dir.path not in sys.path:
                sys.path.append(conn_dir.path)

            mod_name = f"{conn_dir.name}.connector"
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
        worker.push_exc_handler(timeout_handler)
        worker.work()
