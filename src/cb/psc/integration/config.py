from collections import namedtuple

Config = namedtuple("Config", ["database"])

config = Config(database="sqlite:////private/tmp/pscint.db")
