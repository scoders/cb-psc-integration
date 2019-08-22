import logging

from flask import Flask, abort, jsonify, request
from schema import SchemaError

import cb.psc.integration.database as database
import cb.psc.integration.workers as workers
from cb.psc.integration.config import config
from cb.psc.integration.utils import (
    AnalyzeSchema,
    JobSchema,
    RemoveAnalysesSchema,
    RetrieveAnalysesSchema
)

log = logging.getLogger()
log.setLevel(config.loglevel)

app = Flask(__name__)


@app.teardown_request
def remove_session(ex=None):
    database.session.commit()
    database.session.remove()


@app.route("/job", methods=["POST"])
def job():
    req = request.get_json(force=True)
    log.debug(f"/job: {req!r}")

    try:
        req = JobSchema.validate(req)
    except SchemaError as e:
        abort(400, str(e))

    return jsonify(success=True)


@app.route("/analyze", methods=["POST"])
def analyze():
    req = request.get_json(force=True)
    log.debug(f"/analyze: {req!r}")

    try:
        req = AnalyzeSchema.validate(req)
    except SchemaError as e:
        abort(400, str(e))

    if "hashes" in req:
        hashes = req.get("hashes")
        if not isinstance(hashes, list) or len(hashes) < 1:
            abort(400)
        workers.binary_retrieval.enqueue(workers.fetch_binaries, hashes)
        log.debug(f"enqueued retrieval of {len(hashes)} binaries")
    else:
        workers.binary_retrieval.enqueue(
            workers.fetch_query, req.get("query"), limit=req.get("limit")
        )

    return jsonify(success=True)


def retrieve_analyses(req):
    log.debug(f"retrieve_analyses: {req}")

    try:
        req = RetrieveAnalysesSchema.validate(req)
    except SchemaError as e:
        abort(400, str(e))

    hashes = req.get("hashes")
    response = {"completed": {}, "pending": workers.active_analyses()}
    for hash in hashes:
        results = database.AnalysisResult.query.filter_by(sha256=hash)
        response["completed"][hash] = [result.as_dict() for result in results]

    return jsonify(success=True, data=response)


def remove_analyses(req):
    # TODO(ww): Remove analyses by hash, by connector name, by job ID
    log.debug(f"remove_analyses: {req}")

    try:
        req = RemoveAnalysesSchema.validate(req)
    except SchemaError as e:
        abort(400, str(e))

    kind = req.get("kind")
    items = req.get("items")
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


@app.route("/hashes", methods=["GET"])
def hashes():
    log.debug(f"/hashes: {request}")

    all_results = database.Binary.query.all()
    return jsonify([r.sha256 for r in all_results])


def main():
    database.init_db()
    app.run(host=config.flask_host, port=config.flask_port, debug=config.is_development)


if __name__ == "__main__":
    main()
