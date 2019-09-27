import importlib
import logging
import os
from functools import lru_cache

import yaml
from cb.psc.integration import workers
from cb.psc.integration.config import config
from cb.psc.integration.database import AnalysisResult
from dataclasses import dataclass
from rq import get_current_job

log = logging.getLogger(__name__)
log.setLevel(config.loglevel)


class ConnectorConfig:
    """
    The parent class for per-connector configuration.

    Individual connectors should assign their `Config` property to a subclass
    of :class:`ConnectorConfig`.
    """

    def __init_subclass__(cls, *args, **kwargs):
        return dataclass(cls)

    @classmethod
    def from_file(cls):
        """
        Loads an instance of this class from a `config.yml` file relative to
        the corresponding connector's source directory.
        """
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
    """
    The parent class for all connectors. Custom connectors should
    inherit from this and override the appropriate methods.
    """

    _instance = None
    available = True

    def __init__(self):
        if self.__class__._instance:
            raise ValueError(f"{self.__class__.__name__} is a singleton")
        else:
            self.__class__._instance = self

    @classmethod
    def instance(cls):
        """
        Returns this connector's singleton.

        :return: The singleton instance of this connector
        :rtype: :class:`Connector`
        """
        if cls._instance is None:
            cls()
        return cls._instance

    @classmethod
    def connectors(cls):
        """
        Yields each known connector that's currently available.

        :rtype: Iterator[:class:`Connector`]
        """
        for konnector in cls.__subclasses__():
            connector = konnector.instance()
            if connector.available:
                yield connector
            else:
                log.warning(f"{connector.name} unavailable: probable initialization error")

    @property
    @lru_cache()
    def config(self):
        """
        Returns the configuration associated with this connector.

        :return: The association config
        :rtype: :class:`ConnectorConfig`
        """
        if self.Config:
            try:
                return self.Config.from_file()
            except yaml.YAMLError as e:
                log.exception(f"{self.name} couldn't parse config")
                raise e
            except IOError as e:
                log.warning(f"{self.name} couldn't read config, trying default")
                return self.Config()
        else:
            log.warning(f"config requested for a connector that doesn't have any")

    @property
    def name(self):
        """
        Returns this connector's name. Connector names should be unique.

        :rtype: str

        Example::

        >>> names = [conn.name for conn in Connector.connectors()]
        """
        return self.__class__.__name__.lower()

    def result(self, binary, **kwargs):
        """
        Returns a new AnalysisResult with the given fields populated, updating
        the database in the background.

        This should be used within the :meth:`analyze` method to create
        analysis results.

        :rtype: :class:`AnalysisResult`

        Example::

        >>> self.result(analysis_name="foo", score=10)
        """
        job = get_current_job()
        result = AnalysisResult.create(
            **kwargs, sha256=binary.sha256, connector_name=self.name, job_id=job.id
        ).normalize()
        return result

    def fetch_result_ids(self):
        conn = self.__class__  # singleton
        result_ids = conn.result_ids
        conn.result_ids = []
        return result_ids

    def cache_result_id(self, result_id):
        conn = self.__class__  # singleton
        conn.result_ids.append(result_id)

    def init_result_ids(self):
        conn = self.__class__  # singleton
        conn.result_ids = []

    def batch_and_enqueue_dispatch(self, results):
        log.info(f"{self.name}: enqueuing results dispatch")

        if self.name not in config.sinks:
            log.warning(f"no sink mapped to {self.name} connector; not dispatching result")
            return

        self.init_result_ids()

        num_results = 0
        for result in results:  # results is a generator
            self.cache_result_id(result.id)
            num_results += 1
            if num_results % config.feed_size == 0:
                log.debug(f"{self.name}: {num_results} results so far; sending dispatch request")
                workers.result_dispatch.enqueue(workers.dispatch_result, self.fetch_result_ids())

        result_ids = self.fetch_result_ids()
        if result_ids:  # leftover results
            log.debug(
                f"{self.name}: {num_results} so far; sending dispatch request for {len(result_ids)} leftover results"
            )
            workers.result_dispatch.enqueue(workers.dispatch_result, result_ids)

        log.info(f"{self.name}: dispatched {num_results} results in total")

    def add_job_meta(self):
        job = get_current_job()
        job.meta["conn"] = self  # for identification during timeout handling
        job.save_meta()

    def _analyze(self, binary):
        log.info(f"{self.name}: analyzing binary {binary.sha256}")
        self.add_job_meta()
        data = workers.redis.get(binary.data_key)
        results = self.analyze(binary, data)
        self.batch_and_enqueue_dispatch(results)
        refcount = workers.redis.decr(binary.count_key)
        if refcount < 0:
            log.info(f"weird: refcount < 0 for cached binary: {binary.sha256}")
        elif refcount == 0:
            workers.binary_cleanup.enqueue(workers.flush_binary, binary)
        else:
            log.info(f"binary {binary.sha256} has {refcount} references remaining")
        return results

    def analyze(self, binary, data):
        """
        Overridden by individual connectors; called whenever a binary is ready to be
        analyzed.

        Expected to return a list of :class:`AnalysisResult`.
        """
        log.warning("analyze() called on top-level Connector")
        return []


connectors = Connector.connectors
