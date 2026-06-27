"""
utils/logger.py
───────────────
Centralised logging configuration for the trading framework.

Call ``setup_logging()`` exactly once from main.py before any other
import that creates loggers.  All modules use the standard-library
``logging.getLogger(__name__)`` pattern — this module only configures
the root logger so every child logger inherits the format and level.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with a human-readable format.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Read from the ``LOG_LEVEL`` environment variable by the
               caller (main.py).  Defaults to INFO.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Avoid duplicate handlers on repeated calls
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)-28s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
