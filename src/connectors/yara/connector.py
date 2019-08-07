import logging
import os
from base64 import b64encode
from functools import lru_cache
from pathlib import Path

import yara

from cb.psc.integration.connector import Connector, ConnectorConfig

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class YaraConfig(ConnectorConfig):
    rules_directory: str = os.path.join(os.path.dirname(__file__), "yara_rules")
    error_on_warning: bool = True
    includes: bool = True
    timeout: int = 60
    default_score: int = 100


class YaraConnector(Connector):
    Config = YaraConfig
    name = "yara"

    # TODO(ww): Compiled rule caching.
    @property
    @lru_cache()
    def yara_rules(self):
        # NOTE(ww): This is a cached property instead of an instance
        # because yara.Rules objects cannot be pickled.
        log.debug("compiling YARA rules")
        rule_map = {}
        for entry in os.scandir(self.config.rules_directory):
            if not entry.is_file():
                continue
            rule_map[Path(entry.name).stem] = entry.path

        log.info(f"yara rule map: {rule_map}")

        try:
            return yara.compile(
                filepaths=rule_map, error_on_warning=self.config.error_on_warning, includes=self.config.includes
            )
        except yara.YaraError as e:
            log.error(f"couldn't compile YARA rules: {e}")
            self.available = False
            return []

    def analyze(self, binary, data):
        try:
            matches = self.yara_rules.match(data=data, timeout=self.config.timeout)
        except yara.TimeoutError:
            log.warning(f"{self.name} timed out while analyzing {binary.sha256}")
            return self.result(binary, analysis_name="timeout", error=True)
        except yara.Error as e:
            log.error(f"{self.name} couldn't analyze {binary.sha256}: {e}")
            return self.result(binary, analysis_name="exception", error=True)

        log.info(f"{self.name}: {len(matches)} matches")

        results = []
        for match in matches:
            strings = []
            for string in match.strings:
                strings.append({"offset": string[0], "identifier": string[1], "data": b64encode(string[2]).decode()})

            analysis_name = f"{match.namespace}:{match.rule}"
            score = match.meta.get("score")
            if score is None:
                score = self.config.default_score
                log.warning(f"{analysis_name} does not provide a score, using default score ({score})")

            results.append(
                self.result(binary, analysis_name=analysis_name, score=match.meta.get("score"), payload=strings)
            )

        return results
