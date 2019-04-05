from collections import namedtuple

Config = namedtuple(
    "Config",
    [
        "cbth_profile",
        "database",
        "flask_host",
        "flask_port",
        "redis_host",
        "redis_port",
        "binary_timeout",
    ],
)

# TODO(ww): Load config from file.

config = Config(
    cbth_profile="default",
    database="sqlite:////private/tmp/pscint.db",
    flask_host="localhost",
    flask_port=5000,
    redis_host="localhost",
    redis_port=6379,
    binary_timeout=None,  # NOTE(ww): Set to an int for a timeout in seconds.
)
