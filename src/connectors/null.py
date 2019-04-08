import logging

from cb.psc.integration.connector import Connector

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# TODO(ww): Remove after testing is done.
class NullConnector(Connector):
    name = "null"

    def analyze(self, binary, stream):
        log.info(f"analyzing binary {binary.sha256}")

        return self.result(
            binary,
            analysis_name=self.name,
            score=100,
        )
