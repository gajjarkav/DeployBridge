import logging
import sys

from .config import get_settings


settings = get_settings()

def get_logger(name: str = settings.APP_NAME) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(settings.LOG_LEVEL)
        logger.propagate = False

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.LOG_LEVEL)

        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

        logger.addHandler(handler)

    return logger


logger = get_logger()