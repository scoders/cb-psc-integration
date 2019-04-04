from collections import namedtuple

Config = namedtuple("Config", ["database", "flask_host", "flask_port"])

# TODO(ww): Load config from file.

config = Config(
    database="sqlite:////private/tmp/pscint.db", flask_host="localhost", flask_port=5000
)
