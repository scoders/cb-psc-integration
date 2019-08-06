import logging

from flask import Flask, abort, request, jsonify

import cbapi.psc.threathunter as threathunter

from cb.psc.integration.config import config
from cb.psc.integration.utils import cbth
import cb.psc.integration.database as database
import cb.psc.integration.workers as workers

log = logging.getLogger()
log.setLevel(config.loglevel)

app = Flask(__name__)


@app.teardown_request
def remove_session(ex=None):
    database.session.commit()
    database.session.remove()


@app.route("/analyze", methods=["POST"])
def analyze():
    req = request.get_json(force=True)
    log.debug(f"/analyze: {req!r}")

    if "hashes" in req:
        hashes = req.get("hashes")
        if not isinstance(hashes, list) or len(hashes) < 1:
            abort(400)
        workers.binary_retrieval.enqueue(workers.fetch_binaries, hashes)
        log.debug(f"enqueued retrieval of {len(hashes)} binaries")
    elif "query" in req:
        workers.binary_retrieval.enqueue(workers.fetch_query, req.get("query"), limit=req.get("limit"))
    else:
        abort(400)

    return jsonify(success=True)


def retrieve_analyses(req):
    log.debug(f"retrieve_analyses: {req}")
    hashes = req.get("hashes")

    if not isinstance(hashes, list) or len(hashes) < 1:
        abort(400)

    response = {"completed": {}, "pending": workers.active_analyses()}
    for hash in hashes:
        results = database.AnalysisResult.query.filter_by(sha256=hash)
        response["completed"][hash] = [result.as_dict() for result in results]

    return jsonify(success=True, data=response)


def remove_analyses(req):
    # TODO(ww): Remove analyses by hash, by connector name, by job ID
    log.debug(f"remove_analyses: {req}")

    kind = req.get("kind")
    items = req.get("items")

    if not isinstance(items, list):
        return jsonify(success=False, message="Expected items to be a list")

    # TODO(ww): Could parameterize this to de-duplicate.
    if kind == "hashes":
        query = database.AnalysisResult.sha256.in_(items)
    elif kind == "connector_names":
        query = database.AnalysisResult.connector_name.in_(items)
    elif kind == "analysis_names":
        query = database.AnalysisResult.analysis_name.in_(items)
    elif kind == "job_ids":
        query = database.AnalysisResult.job_id.in_(items)
    else:
        return jsonify(success=False, message="Unknown removal kind")

    # TODO(ww): Probably not very efficient, doing
    # this on the __table__ would probably be a bit
    # faster.
    results = database.AnalysisResult.query.filter(query)
    results.delete(synchronize_session=False)

    return jsonify(success=True)


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
    app.run(host=config.flask_host, port=config.flask_port, debug=config.is_development)


if __name__ == "__main__":
    main()
