"""Application file logging: pipeline progress + errors with tracebacks.

Log file lives in the program's main folder (project root from source,
exe folder in the packaged build), falling back to the temp dir if that
is unwritable. Logging must never crash the app.
"""

import logging
import logging.handlers
import sys
import tempfile
from pathlib import Path

LOGGER_NAME = "scriptboarder"
LOG_FILENAME = "scriptboarder.log"
_MAX_BYTES = 2_000_000
_BACKUP_COUNT = 3


def default_log_dir() -> Path:
    """Program main folder: exe dir when packaged, project root from source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def setup_logging(log_dir: Path | None = None) -> Path | None:
    """Configure file logging. Returns the log file path, None if impossible.

    Never raises: a broken log location must not take down the app.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:  # already configured
        return Path(logger.handlers[0].baseFilename)

    if log_dir is not None:
        candidates = [Path(log_dir), Path(tempfile.gettempdir())]
    else:
        candidates = [default_log_dir(), Path(tempfile.gettempdir())]

    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                directory / LOG_FILENAME,
                encoding="utf-8",
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
            )
        except OSError:
            continue
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        return Path(handler.baseFilename)
    return None


def log_progress(msg: str) -> None:
    logging.getLogger(LOGGER_NAME).info(msg)


def log_error(context: str, exc: BaseException | None = None) -> None:
    """Log a failure with its traceback; exc=None uses the in-flight exception."""
    logging.getLogger(LOGGER_NAME).error(
        f"{context}: {exc}", exc_info=exc if exc is not None else True
    )


def shutdown() -> None:
    """Close handlers (tests / app exit)."""
    logger = logging.getLogger(LOGGER_NAME)
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)
