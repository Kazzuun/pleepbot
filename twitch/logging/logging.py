import json
import logging
import logging.config
import logging.handlers
import os
from typing import Union


__all__ = (
    "logger", 
    "setup_logging", 
    "TaskEventFilter"
)


logger = logging.getLogger("twitch")


class TaskEventFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> Union[bool, logging.LogRecord]:
        filtered_modules = ("base_events", "aiohttp")
        return not (record.module in filtered_modules)


def setup_logging():
    # These folders must match the folder in config.json file handler -> filename
    if not os.path.exists("logs"):
        os.mkdir("logs")
    if not os.path.exists("logs/twitch"):
        os.mkdir("logs/twitch")

    config_file = f"{os.path.realpath(os.path.dirname(__file__))}/config.json"
    with open(config_file) as conf:
        config = json.load(conf)
    logging.config.dictConfig(config)

