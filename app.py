import logging

from flask import Flask, abort, request, jsonify
from rq import Queue

from cb.psc.integration.config import config
from cb.psc.integration import database
from cb.psc.integration.connector import Connector
from cb.psc.integration.workers import conn as redis
from cb.psc.integration.ubs import fetch_binaries

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

app = Flask(__name__)

binary_retrieval = Queue("binary_retrieval", connection=redis)


class NullConnector(Connector):
    name = "null"

    def analyze(self, binary, stream):
        log.info(f"analyzing binary {binary.sha256}")

        return self.result(
            binary,
            analysis_name=self.name,
            score=100,
        )


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

    binary_retrieval.enqueue(fetch_binaries, hashes)
    log.debug(f"enqueued retrieval of {len(hashes)} binaries")

    return jsonify(success=True)


@app.route("/analysis", methods=["GET"])
def analysis():
    req = request.get_json(force=True)
    logging.debug(f"/analysis: {req!r}")

    hashes = req.get("hashes")

    if not isinstance(hashes, list) or len(hashes) < 1:
        abort(400)

    response = {}
    # for hash in hashes:
    #     results = AnalysisResult.query.filter_by(sha256=hash)
    #     response[hash] = [result.as_dict() for result in results]

    return jsonify(success=True, data=response)


def main():
    # TODO(ww): Config.
    database.init_db()
    app.run(host=config.flask_host, port=config.flask_port)


if __name__ == '__main__':
    main()
