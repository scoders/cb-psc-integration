import functools
import logging
from itertools import zip_longest

import cbapi.psc.threathunter as threathunter
import validators
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

AnalyzeSchema = Schema(
    Or(
        {"hashes": And([str], len)},
        {"query": And(str, len), Optional("limit"): And(int, lambda n: n > 0)},
    )
)

RetrieveAnalysesSchema = Schema({"hashes": And([str], len)})

# TODO(ww): Validate individual items as well.
RemoveAnalysesSchema = Schema(
    Or(
        {"kind": "hashes", "items": And([str], validators.sha256)},
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
