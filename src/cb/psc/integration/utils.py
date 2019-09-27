import functools
import logging
from itertools import zip_longest

import cbapi.psc.threathunter as threathunter
import dateutil.parser
import validators
from cb.psc.integration import workers
from cb.psc.integration.config import config
from croniter import croniter
from rq.timeouts import JobTimeoutException
from schema import And, Optional, Or, Schema, Use

log = logging.getLogger()
log.setLevel(config.loglevel)


AddJobSchema = Schema(
    {
        "query": And(str, len),
        "schedule": And(str, croniter.is_valid),
        "repeat": Or("forever", And(int, lambda n: n > 0)),
        Optional("limit"): And(int, lambda n: n > 0),
    }
)

RemoveJobSchema = Schema({"job_id": And(str, len)})

GetJobsSchema = Schema({"until": Or("forever", And(str, Use(dateutil.parser.parse)))})

AnalyzeSchema = Schema(
    Or(
        {"hashes": And([str], len)},
        {"query": And(str, len), Optional("limit"): And(int, lambda n: n > 0)},
    )
)

RetrieveAnalysesSchema = Schema({"hashes": And([str], len)})

RemoveAnalysesSchema = Schema(
    Or(
        {"kind": "hashes", "items": And([str], [validators.sha256])},
        {"kind": "connector_names", "items": And([str], len)},
        {"kind": "analysis_names", "items": And([str], len)},
        {"kind": "job_ids", "items": And([str], len)},
    )
)


@functools.lru_cache()
def cbth():
    return threathunter.CbThreatHunterAPI(profile=config.cbth_profile)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args)


def timeout_handler(job, exc_type, exc_value, traceback):
    if not isinstance(exc_value, JobTimeoutException):
        return True  # continue chaining exc handlers

    log.info(f"Caught timeout exception for job: {job}, job_id: {job.id},  {job.func_name}")
    if job.func_name != "_analyze":
        return True

    conn = job.meta["conn"]
    if not conn:
        return True

    result_ids = conn.fetch_result_ids()
    log.info(f"Dispatching {len(result_ids)} leftover results for conn: {conn.name}")
    if result_ids:  # leftover results
        workers.result_dispatch.enqueue(workers.dispatch_result, result_ids)
    return False
