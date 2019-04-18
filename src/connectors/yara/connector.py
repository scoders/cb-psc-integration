import logging
import os
from pathlib import Path

import yara

from cb.psc.integration.connector import Connector

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class YaraConnector(Connector):
    name = "yara"
    # TODO(ww): Provide an API for connector configs.
    config = {
        "rules_directory": os.path.join(os.path.dirname(__file__), "yara_rules"),
        "error_on_warning": True,
        "includes": True,
    }

    def __init__(self):
        super().__init__()
        self.yara_rules = self.compile_rules()

    def compile_rules(self):
        rule_map = {}
        for entry in os.scandir(self.config["rules_directory"]):
            if not entry.is_file():
                continue
            rule_map[Path(entry.name).stem] = entry.path

        log.info(f"yara rule map: {rule_map}")

        try:
            return yara.compile(
                filepaths=rule_map,
                error_on_warning=self.config["error_on_warning"],
                includes=self.config["includes"],
            )
        except yara.YaraError as e:
            log.error(f"couldn't compile YARA rules: {e}")
            self.available = False
            return []

    def analyze(self, binary, data):
        return self.result(binary, analysis_name=self.name, score=100)
