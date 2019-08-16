import functools
import logging
from itertools import zip_longest

import cbapi.psc.threathunter as threathunter

from cb.psc.integration.config import config
from schema import And, Optional, Or, Schema

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


@functools.lru_cache()
def cbth():
    return threathunter.CbThreatHunterAPI(profile=config.cbth_profile)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args)
