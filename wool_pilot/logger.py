import logging
from pythonjsonlogger.json import JsonFormatter


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(reserved_attrs=[]))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            handler,
        ],
    )
