import logging

from flask import Flask, abort, request, jsonify

from cb.psc.integration.config import config
import cb.psc.integration.database as database
import cb.psc.integration.workers as workers

logging.basicConfig()
log = logging.getLogger()
log.setLevel(config.loglevel)

app = Flask(__name__)


@app.teardown_request
def remove_session(ex=None):
    database.session.remove()


@app.route("/analyze", methods=["POST"])
def analyze():
    req = request.get_json(force=True)
    log.debug(f"/analyze: {req!r}")

    hashes = req.get("hashes")

    if not isinstance(hashes, list) or len(hashes) < 1:
        abort(400)

    workers.binary_retrieval.enqueue(workers.fetch_binaries, hashes)
    log.debug(f"enqueued retrieval of {len(hashes)} binaries")

    return jsonify(success=True)


def retrieve_analyses(req):
    log.debug(f"retrieve_analyses: {req}")
    hashes = req.get("hashes")

    if not isinstance(hashes, list) or len(hashes) < 1:
        abort(400)

    response = {
        "completed": {},
        "pending": workers.active_analyses(),
    }
    for hash in hashes:
        results = database.AnalysisResult.query.filter_by(sha256=hash)
        response["completed"][hash] = [result.as_dict() for result in results]

    return jsonify(success=True, data=response)


def remove_analyses(req):
    log.debug(f"remove_analyses: {req}")
    # TODO(ww): Remove analyses by hash, by connector name, by job ID
    hashes = req.get("hashes")


@app.route("/analysis", methods=["GET", "DELETE"])
def analysis():
    log.debug(f"/analysis: {request}")
    req = request.get_json(force=True)
    if request.method == "GET":
        return retrieve_analyses(req)
    elif request.method == "DELETE":
        return remove_analyses(req)


def main():
    database.init_db()
    app.run(host=config.flask_host, port=config.flask_port)


if __name__ == '__main__':
    main()
