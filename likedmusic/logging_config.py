"""Centralised logging setup for LikedMusic."""

import logging
import logging.handlers

from likedmusic.config import DATA_DIR

LOG_FILE = DATA_DIR / "likedmusic.log"


def setup_logging() -> None:
    """Configure root logger: DEBUG+ to rotating file, WARNING+ to stderr."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # File: always DEBUG+
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Console: WARNING+ only (same as before)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    root.addHandler(fh)
    root.addHandler(ch)
