import functools
import logging
from itertools import zip_longest

import cbapi.psc.threathunter as threathunter
import dateutil.parser
import validators
from croniter import croniter
from schema import And, Optional, Or, Schema, Use

from cb.psc.integration.config import config
from rq.timeouts import JobTimeoutException
from cb.psc.integration import workers
import cb.psc.integration.connector as connector

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
        return False
    log.info(f"Caught timeout exception for job: {job},  {job.func_name}")
    if job.func_name != '_analyze':
        return False
    for conn in connector.connectors():
        result_ids = conn.fetch_result_ids()
        log.info(f"Dispatching {len(result_ids)} leftover results for conn: {conn.name}")
        if result_ids:  # leftover results
            workers.result_dispatch.enqueue(workers.dispatch_result, result_ids)
    return True


