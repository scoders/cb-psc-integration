import logging

import redis as r
from rq import Worker, Queue, Connection

from cb.psc.integration.config import config

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

listen = ["binary_retrieval", "binary_analysis"]

redis = r.Redis(host=config.redis_host, port=config.redis_port)

if __name__ == "__main__":
    with Connection(redis):
        worker = Worker(list(map(Queue, listen)))
        worker.work()