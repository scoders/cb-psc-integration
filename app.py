from cb.psc.integration import database
from cb.psc.integration.connector import Connector
from cb.psc.integration.database import Binary

import logging
import sys

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class NullConnector(Connector):
    name = "null"

    def analyze(self, binary, stream):
        logger.info(f"analyzing binary {binary.sha256}")

        return self.result(
            binary,
            analysis_name=self.name,
            score=100,
        )


def fetch_binary(hash):
    # TODO(ww): De-stub.
    b = Binary.from_hash(hash)

    if not b:
        b = Binary.create(sha256=hash)

    return (b, "")


def main():
    # TODO(ww): Config.
    database.Base.metadata.create_all(database.engine)

    # TODO(ww): How do we want to feed binaries into the sandbox?
    # Some ideas:
    # * Open a port and listen on it for lines of hashes
    # * Microservice and listen for POSTs of hashes
    # * Microservice and listen for POST of process queries
    #   * Then execute the process queries and extract the hashes
    # Once we have the hashes, pull binaries from the UBS.

    for connector in Connector.connectors():
        logger.info(connector.name)

    for line in sys.stdin:
        line = line.rstrip()

        binary, stream = fetch_binary(line)

        for connector in Connector.connectors():
            result = connector.analyze(binary, stream)
            logger.info(f"analysis: {result.score}")


if __name__ == '__main__':
    main()
