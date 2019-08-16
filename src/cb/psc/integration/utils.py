import functools
import logging
from itertools import zip_longest

import cbapi.psc.threathunter as threathunter
from schema import And, Optional, Or, Schema

from cb.psc.integration.config import config

log = logging.getLogger()
log.setLevel(config.loglevel)

JobSchema = Schema(
    {
        "query": And(str, len),
        "schedule": And(str, len),
        "repeat": Or("forever", And(int, lambda n: n > 0)),
        Optional("limit"): And(int, lambda n: n > 0),
    }
)

AnalyzeHashesSchema = Schema({"hashes": And([str], len)})
AnalyzeQuerySchema = Schema({"query": And(str, len), Optional("limit"): And(int, lambda n: n > 0)})

RetrieveAnalysesSchema = Schema({"hashes": And([str], len)})

# TODO(ww): Validate individual items as well.
RemoveAnalysesSchema = Schema(
    {"kind": Or("hashes", "connector_names", "analysis_names", "job_ids"), "items": And([str], len)}
)


@functools.lru_cache()
def cbth():
    return threathunter.CbThreatHunterAPI(profile=config.cbth_profile)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args)
