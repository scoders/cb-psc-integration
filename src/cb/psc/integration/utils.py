import functools
import logging

import cbapi.psc.threathunter as threathunter
from cb.psc.integration.config import config

log = logging.getLogger()
log.setLevel(config.loglevel)


@functools.lru_cache()
def cbth():
    return threathunter.CbThreatHunterAPI(profile=config.cbth_profile)
