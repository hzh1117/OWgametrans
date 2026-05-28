import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level=logging.INFO):
    log_dir = Path(__file__).parent.parent / "logs"
    try:
        log_dir.mkdir(exist_ok=True)
    except OSError:
        pass

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(RotatingFileHandler(
            log_dir / "gametrans.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ))
    except OSError:
        pass

    logging.basicConfig(level=level, format=fmt, handlers=handlers)
    return logging.getLogger("gametrans")
