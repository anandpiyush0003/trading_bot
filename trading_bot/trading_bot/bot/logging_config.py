"""
logging_config.py
------------------
Central logging setup for the trading bot.

Design goals:
- Every API request, response, and error is logged to a rotating file
  (logs/trading_bot.log) so a full audit trail exists for every order.
- The console only shows human-friendly, high-level messages (INFO+),
  keeping CLI output clean while the file captures full detail (DEBUG+).
- Sensitive data (API keys/secrets) is NEVER written to the log.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_CONFIGURED = False


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure and return the root application logger.

    Idempotent: safe to call multiple times (e.g. from tests or CLI re-entry).

    Args:
        verbose: if True, also print DEBUG-level messages to the console.

    Returns:
        The configured 'trading_bot' logger instance.
    """
    global _CONFIGURED
    logger = logging.getLogger("trading_bot")

    if _CONFIGURED:
        return logger

    os.makedirs(LOG_DIR, exist_ok=True)

    logger.setLevel(logging.DEBUG)  # capture everything; handlers filter what's shown/stored

    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(fmt="%(levelname)-8s | %(message)s")

    # Rotating file handler: keeps logs bounded (5MB x 3 backups) but persistent.
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    _CONFIGURED = True
    return logger


def get_logger() -> logging.Logger:
    """Return the app logger, configuring it with defaults if not already done."""
    return setup_logging() if not _CONFIGURED else logging.getLogger("trading_bot")
