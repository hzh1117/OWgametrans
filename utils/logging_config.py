import logging
import sys
from pathlib import Path


def setup_logging(level=logging.INFO):
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "gametrans.log", encoding="utf-8"),
    ]

    logging.basicConfig(level=level, format=fmt, handlers=handlers)
    return logging.getLogger("gametrans")
