import logging

from flask import Flask, abort, request, jsonify

from cb.psc.integration.config import config
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
        # TODO(ww): Probably not very efficient, doing
        # this on the __table__ would probably be a bit
        # faster.
        results = database.AnalysisResult.query.filter(
            database.AnalysisResult.sha256.in_(items)
        )
    elif kind == "connector_names":
        results = database.AnalysisResult.query.filter(
            database.AnalysisResult.connector_name.in_(items)
        )
    elif kind == "analysis_names":
        results = database.AnalysisResult.query.filter(
            database.AnalysisResult.analysis_name.in_(items)
        )
    elif kind == "job_ids":
        results = database.AnalysisResult.query.filter(
            database.AnalysisResult.job_id.in_(items)
        )
    else:
        return jsonify(success=False, message="Unknown removal kind")

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
