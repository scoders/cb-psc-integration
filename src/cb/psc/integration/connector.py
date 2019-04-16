import logging

from rq import get_current_job

from .database import AnalysisResult
import cb.psc.integration.workers as workers

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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
        job = get_current_job()
        return AnalysisResult.create(
            sha256=binary.sha256, connector_name=self.name, job_id=job.id, **kwargs
        )

    def _analyze(self, binary):
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
