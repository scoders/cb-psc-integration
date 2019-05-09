import logging
from functools import lru_cache
from dataclasses import dataclass
import os
import importlib

from rq import get_current_job
import yaml

from .config import config
from .database import AnalysisResult
import cb.psc.integration.workers as workers

log = logging.getLogger(__name__)
log.setLevel(config.loglevel)


class ConnectorConfig:
    def __init_subclass__(cls, *args, **kwargs):
        return dataclass(cls)

    @classmethod
    def from_file(cls):
        log.debug(f"loading config from file for {cls.__name__}")
        # NOTE(ww): __file__ here refers to the base config file, so we need
        # to grab the module and resolve the file from there.
        conn_mod = importlib.import_module(cls.__module__)
        config_filename = os.path.join(os.path.dirname(conn_mod.__file__), "config.yml")
        with open(config_filename, "r") as config_file:
            config_data = yaml.load(config_file)
            log.info(f"loaded config data: {config_data}")
            return cls(**config_data)


class Connector(object):
    _instance = None
    available = True

    def __init__(self):
        if self.__class__._instance:
            raise ValueError(f"{self.__class__.__name__} is a singleton")
        else:
            self.__class__._instance = self

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls()
        return cls._instance

    @classmethod
    def connectors(cls):
        for konnector in cls.__subclasses__():
            connector = konnector.instance()
            if connector.available:
                yield connector
            else:
                log.warning(
                    f"{connector.name} unavailable -- probable initialization error"
                )

    @property
    @lru_cache()
    def config(self):
        if self.konfig:
            try:
                return self.konfig.from_file()
            except yaml.YAMLError as e:
                log.exception(f"{self.name} couldn't parse config")
                raise e
            except IOError as e:
                log.warning(f"{self.name} couldn't read config, trying default")
                return self.konfig()
        else:
            log.warn(f"config requested for a connector that doesn't have any")

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def result(self, binary, **kwargs):
        job = get_current_job()
        return AnalysisResult.create(
            **kwargs, sha256=binary.sha256, connector_name=self.name, job_id=job.id
        )

    def _analyze(self, binary):
        log.info(f"{self.name}: analyzing binary {binary.sha256}")
        data = workers.redis.get(binary.data_key)
        result = self.analyze(binary, data)

        refcount = workers.redis.decr(binary.count_key)

        if refcount < 0:
            log.info(f"weird: refcount < 0 for cached binary: {binary.sha256}")

        workers.binary_cleanup.enqueue(workers.flush_binary, binary)
        return result

    def analyze(self, binary, data):
        log.warning("analyze() called on top-level Connector")


connectors = Connector.connectors
