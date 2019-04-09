import logging
import os
import os.path
import importlib.util
import sys

from .config import config
from .database import Binary, AnalysisResult
from .workers import redis, binary_analysis

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def analyze_binary(hash):
    log.debug(f"analyzing binary: {hash}")
    log.debug(f"connectors: {', '.join(c.name for c in Connector.connectors())}")

    for connector in Connector.connectors():
        log.debug(f"running {connector.name} analysis")
        binary = Binary.from_hash(hash)
        data = redis.get(hash)
        binary_analysis.enqueue(connector.analyze, binary, data)
        # TODO(ww): Need to track all analyses and
        # evict the binary from redis once all are done.


def load_connectors():
    log.debug("loading connectors")
    for path in config.connector_dirs:
        if not os.path.isdir(path):
            log.warning(f"{path} is not a directory, skipping")
            continue

        log.info(f"searching path: {path}")
        for conn_dir in os.scandir(path):
            if not conn_dir.is_dir():
                log.debug(f"{conn_dir.path} is not a directory, skipping")
                continue

            conn_file = os.path.join(conn_dir.path, "connector.py")
            if not os.path.isfile(conn_file):
                log.warning(f"{conn_file} does not exist, skipping")
                continue

            conn_mod = f"connectors.{conn_dir.name}"
            log.info(f"loading {conn_file} as {conn_mod}")
            try:
                spec = importlib.util.spec_from_file_location(conn_mod, conn_file)
                connector = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(connector)

                # Gross. But apparently the "correct" way to get
                # dynamically loaded modules to work with Pickle.
                sys.modules[conn_mod] = connector
            except Exception as e:
                log.error(f"failed to load {conn_file}: {e}")

    log.info(f"loaded connectors: {', '.join(c.name for c in Connector.connectors())}")


class Connector(object):
    __instance = None

    def __init__(self):
        if self.__class__.__instance:
            raise ValueError(f"{self.__class__.__name__} is a singleton")
        else:
            self.__class__.__instance = self

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls()
        return cls.__instance

    @classmethod
    def connectors(cls):
        for konnector in cls.__subclasses__():
            yield konnector.instance()

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def result(self, binary, **kwargs):
        return AnalysisResult.create(
            sha256=binary.sha256, connector_name=self.name, **kwargs
        )

    def analyze(self, binary, data):
        log.warning("analyze() called on top-level Connector")
