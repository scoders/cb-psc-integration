from .database import AnalysisResult

import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def analyze_binary(hash):
    log.debug(f"analyze_binary: {hash}")

    for connector in Connector.connectors():
        pass


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

    def analyze(self, binary, stream):
        log.warning("analyze() called on top-level Connector")
