import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "mqtt_bridge.log")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 5              # Keep last 5 rotated files


def setup_logger(name: str = "mqtt_bridge") -> logging.Logger:
    """
    Returns a logger that writes to both the console and a rotating log file.
    Call this once at startup; every module that does `logging.getLogger()`
    afterwards will inherit the same handlers automatically.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:          # Avoid adding duplicate handlers on reload
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ──────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # ── Rotating file handler ─────────────────────────────────────────────────
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)   # capture DEBUG → file only
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger