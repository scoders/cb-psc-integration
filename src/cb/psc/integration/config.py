from typing import List, Optional, NamedTuple
import os


class Config(NamedTuple):
    environment: str
    loglevel: str
    cbth_profile: str
    database: str
    flask_host: str
    flask_port: int
    redis_host: str
    redis_port: int
    binary_timeout: Optional[int]
    connector_dirs: List[str]


# TODO(ww): Load config from file.

config = Config(
    environment=os.getenv("ENVIRONMENT", "development"),
    loglevel=os.getenv("LOGLEVEL", "DEBUG"),
    cbth_profile="default",
    database="sqlite:////private/tmp/pscint.db",
    flask_host="localhost",
    flask_port=5000,
    redis_host="localhost",
    redis_port=6379,
    binary_timeout=None,  # NOTE(ww): Set to an int for a timeout in seconds.
    connector_dirs=[
        "/usr/share/cb/integrations",
    ],
)

if config.environment == "development":
    conn_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../connectors"))
    config.connector_dirs.append(conn_dir)
