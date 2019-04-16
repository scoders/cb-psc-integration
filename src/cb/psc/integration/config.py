from typing import List, Optional, NamedTuple
import os


class Config(NamedTuple):
    environment: str = "production"
    loglevel: str = "INFO"
    cbth_profile: str = "default"
    database: str = "sqlite:////usr/share/cb/psc.db"
    flask_host: str = "localhost"
    flask_port: int = 5000
    redis_host: str = "localhost"
    redis_port: int = 6379
    binary_timeout: Optional[int] = 60  # TODO(ww): Maybe default to None?
    connector_dirs: List[str] = ["/usr/share/cb/integrations"]

    @classmethod
    def development(cls):
        return cls(
            environment="development",
            loglevel="DEBUG",
            database="sqlite:////private/tmp/psc.db",
            binary_timeout=None,
            connector_dirs=[
                "/usr/share/cb/integrations",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../connectors")),
            ],
        )


# TODO(ww): Load config from file.

config = Config.development()
