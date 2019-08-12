import functools
import logging
from itertools import zip_longest
from typing import NamedTuple

import cbapi.psc.threathunter as threathunter

from cb.psc.integration.config import config

log = logging.getLogger()
log.setLevel(config.loglevel)


@functools.lru_cache()
def cbth():
    return threathunter.CbThreatHunterAPI(profile=config.cbth_profile)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args)
