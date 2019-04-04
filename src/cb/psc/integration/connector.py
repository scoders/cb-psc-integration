import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Connector(object):
    """docstring for Connector"""

    def __init__(self):
        super(Connector, self).__init__()

    @classmethod
    def connectors(cls):
        for konnector in cls.__subclasses__:
            yield konnector.instance

    @property
    def name(self):
        return None
