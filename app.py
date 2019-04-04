import logging

from flask import Flask, abort, request, jsonify

from cb.psc.integration.config import config
from cb.psc.integration import database
from cb.psc.integration.connector import Connector
from cb.psc.integration.database import Binary, AnalysisResult


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app = Flask(__name__)


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

    logger.debug(f"binary: {b.sha256}")

    return (b, "")


@app.teardown_request
def remove_session(ex=None):
    database.session.remove()


@app.route("/analyze", methods=["POST"])
def analyze():
    req = request.get_json(force=True)
    logging.debug(f"/analyze: {req!r}")

    hashes = req.get("hashes")

    if not isinstance(hashes, list) or len(hashes) < 1:
        abort(400)

    for hash in hashes:
        for connector in Connector.connectors():
            binary, stream = fetch_binary(hash)
            connector.analyze(binary, stream)

    return jsonify(success=True)


@app.route("/analysis", methods=["GET"])
def analysis():
    req = request.get_json(force=True)
    logging.debug(f"/analysis: {req!r}")

    hashes = req.get("hashes")

    if not isinstance(hashes, list) or len(hashes) < 1:
        abort(400)

    response = {}
    for hash in hashes:
        results = AnalysisResult.query.filter_by(sha256=hash)
        response[hash] = [result.as_dict() for result in results]

    return jsonify(success=True, data=response)


def main():
    # TODO(ww): Config.
    database.Base.metadata.create_all(database.engine)
    app.run(host=config.flask_host, port=config.flask_port)


if __name__ == '__main__':
    main()
