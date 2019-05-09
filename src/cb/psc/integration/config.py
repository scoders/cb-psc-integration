import logging
from typing import List, Optional, NamedTuple
import os

import yaml

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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

    @property
    def is_development(self):
        return self.environment == "development"

    @classmethod
    def development(cls):
        return cls(
            environment="development",
            loglevel="DEBUG",
            database="sqlite:////tmp/psc.db",
            binary_timeout=None,
            connector_dirs=[
                "/usr/share/cb/integrations",
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "../../../connectors")
                ),
            ],
        )

    @classmethod
    def production(cls):
        return cls()

    @classmethod
    def load(cls):
        if os.getenv("ENVIRONMENT") == "development":
            log.info("ENVIRONMENT=development set, using default development config")
            return cls.development()

        config_filename = os.path.join(os.path.dirname(__file__), "../../../../config.yml")
        if not os.path.isfile(config_filename):
            log.warning("no config file found, using default production config")
            return cls.production()

        with open(config_filename, "r") as config_file:
            config_data = yaml.load(config_file)
            log.info(f"loaded config data: {config_data}")
            return cls(**config_data)


config = Config.load()
