"""
Logging setup for RIOS.

WHY configured centrally here rather than ad-hoc print()/logging calls in
each module: the audit-trail requirement means every pipeline run needs a
consistent, timestamped, file-backed log — not scattered console output that
disappears when the Streamlit session ends.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rios.core.config import REPO_ROOT, get_settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Safe to call repeatedly (won't duplicate
    handlers) — call this at the top of every module as:
        logger = get_logger(__name__)
    """
    settings = get_settings()
    log_dir = REPO_ROOT / settings.logging.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured — avoid duplicate handlers

    logger.setLevel(settings.logging.level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_dir / "rios.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
