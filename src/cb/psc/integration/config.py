import functools
import logging
import os
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

import yaml

from frozendict import frozendict

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@dataclass(eq=True, frozen=True)
class SinkConfig:
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


@dataclass(eq=True, frozen=True)
class Config:
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

    connector_dirs: Tuple[str, ...] = ("/usr/share/cb/integrations",)
    """
    A list of directories to search for connectors.
    """

    result_sinks: Mapping[str, dict] = field(default_factory=frozendict)
    """
    A mapping of connector names to result sink configurations.
    """

    @property
    @functools.lru_cache()
    def database_url(self):
        """
        Returns a URL suitable for connecting to the binary analysis DB.
        """
        return os.getenv("DATABASE_URL")

    @property
    @functools.lru_cache()
    def redis_url(self):
        """
        Returns a URL suitable for connecting to the redis cache.
        """
        return os.getenv("REDIS_URL")

    @property
    @functools.lru_cache()
    def flask_host(self):
        """
        Returns the domain or IP that the flask frontend is running on.
        """
        return os.getenv("FLASK_HOST")

    @property
    @functools.lru_cache()
    def flask_port(self):
        """
        Returns the port that the flask frontend is running on.
        """
        return os.getenv("FLASK_PORT")

    @property
    def is_development(self):
        """
        Returns true if the environment is a development environment.
        """
        return self.environment == "development"

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
        log.debug(f"sinks: {sinks}")
        return frozendict(sinks)

    @classmethod
    def _normalize_config(cls, config_data):
        if "connector_dirs" in config_data:
            config_data["connector_dirs"] = tuple(config_data["connector_dirs"])
        for con_name, sink_conf in config_data.get("result_sinks", {}).items():
            config_data["result_sinks"][con_name] = frozendict(sink_conf)
        config_data["result_sinks"] = frozendict(config_data.get("result_sinks", {}))
        return config_data

    @classmethod
    def load(cls):
        """
        Creates a :py:class:`Config` object from a `config.yml` file present
        at the root of the binary analysis SDK's source tree.
        """
        if os.getenv("ENVIRONMENT") == "development":
            log.info("ENVIRONMENT=development set")

        config_filename = os.path.join(os.path.dirname(__file__), "../../../../config.yml")
        if not os.path.isfile(config_filename):
            log.warning("no config file found, using default production config")
            return cls()

        with open(config_filename, "r") as config_file:
            config_data = yaml.safe_load(config_file)
            log.info(f"loaded config data: {config_data}")
            config_data = cls._normalize_config(config_data)
            return cls(**config_data)


config = Config.load()
