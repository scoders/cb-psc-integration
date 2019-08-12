import functools
import logging
import os
from typing import Dict, List, NamedTuple, Optional

import yaml

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class SinkConfig(NamedTuple):
    """
    Represents the configuration for a "result sink", i.e.
    an output that the sandbox understands how to dispatch analysis
    results to.
    """

    kind: str
    """
    The kind of sink.
    """

    id: str
    """
    The sink's unique identifier.
    """

    # TODO(ww): This should really be part of the initialization behavior.
    def validate(self):
        if self.kind not in {"feed", "watchlist"}:
            raise TypeError("unknown sink kind")

    def __str__(self):
        return f"{self.kind} {self.id}"


class Config(NamedTuple):
    """
    The primary source of configuration for the binary analysis sandbox.

    Each connector has its own, unrelated, configuration object.
    """

    environment: str = "production"
    """
    The kind of running environment.
    """

    loglevel: str = "INFO"
    """
    The :py:mod:`logging` loglevel to use.
    """

    cbth_profile: str = "default"
    """
    The credential profile to use when interacting with CBAPI/cbapi-python.
    """

    database: str = "sqlite:////usr/share/cb/psc.db"
    """
    The protocol and path to use for the result DB.
    """

    flask_host: str = "localhost"
    """
    The hostname for the flask frontend.
    """

    flask_port: int = 5000
    """
    The port for the flask frontend.
    """

    redis_host: str = "localhost"
    """
    The hostname for the redis cache.
    """

    redis_port: int = 6379
    """
    The port for the redis cache.
    """

    binary_timeout: Optional[int] = 60  # TODO(ww): Maybe default to None?
    """
    The maximum time allotted to each binary analysis task, or 0
    if no timeout.
    """

    binary_fetch_max_retry: Optional[int] = 3
    """
    The maximum number of times to attempt retrieval of a binary from the UBS
    before failing.
    """

    connector_dirs: List[str] = ["/usr/share/cb/integrations"]
    """
    A list of directories to search for connectors.
    """

    result_sinks: Dict[str, dict] = {}
    """
    A mapping of connector names to result sink configurations.
    """

    @property
    def is_development(self):
        """
        Returns true if the environment is a development environment.
        """
        return self.environment == "development"

    @classmethod
    def development(cls):
        """
        Returns a default configuration for a development environment.
        """
        return cls(
            environment="development",
            loglevel="DEBUG",
            database="sqlite:////tmp/psc.db",
            binary_timeout=None,
            connector_dirs=[
                "/usr/share/cb/integrations",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../connectors")),
            ],
        )

    @classmethod
    def production(cls):
        """
        Returns a default configuration for a production environment.
        """
        return cls()

    @classmethod
    def load(cls):
        """
        Creates a :py:class:`Config` object from a `config.yml` file present
        at the root of the binary analysis SDK's source tree.
        """
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

    @property
    @functools.lru_cache()
    def sinks(self):
        log.debug("loading sink configs")
        sinks = {}
        for con_name, sink_config in self.result_sinks.items():
            try:
                sinks[con_name] = SinkConfig(**sink_config)
                sinks[con_name].validate()
            except TypeError as e:
                log.error(f"failed to load sink config for {con_name}: {e}")
        return sinks


config = Config.load()
