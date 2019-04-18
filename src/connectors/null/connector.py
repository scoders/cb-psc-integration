import logging
import time

from cb.psc.integration.connector import Connector

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# TODO(ww): Remove after testing is done.
class NullConnector(Connector):
    name = "null"

    def analyze(self, binary, data):
        time.sleep(15)

        return self.result(binary, analysis_name=self.name, score=100)
