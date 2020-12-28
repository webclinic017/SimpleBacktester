import datetime
import logging
import sys
from src.resources.config import LOGS_DIR

def get_logger(
    name: str,
    to_stdout: bool = True,
    level=None,
) -> logging.Logger:
    """https://realpython.com/python-logging"""
    logger = logging.getLogger(name)
    if level is None:
        level = logging.INFO
    logger.setLevel(level)
    if to_stdout is True:
        # create handler
        c_handler = logging.StreamHandler(stream=sys.stdout)  # console
        # set level
        c_handler.setLevel(level)
        # add formatting
        c_format = logging.Formatter(fmt="%(name)s - %(levelname)s - %(message)s")
        c_handler.setFormatter(fmt=c_format)
        logger.addHandler(hdlr=c_handler)
    logs_path = LOGS_DIR / f"{name}_{datetime.datetime.now()}"
    logs_path.resolve()
    f_handler = logging.FileHandler(logs_path)
    f_handler.setLevel(level)
    f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    f_handler.setFormatter(f_format)
    logger.addHandler(f_handler)
    return logger


if __name__ == "__main__":
    _logger = get_logger(name=__name__)
    _logger.info("This is a debug msg")
    _logger.warning("This is a warning")
    _logger.error("This is an error")
