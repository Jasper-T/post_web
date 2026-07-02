from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from loguru import logger


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DATA_ROOT = Path(os.getenv("WEB_POST_DATA_ROOT", Path(__file__).resolve().parents[3] / "data"))
LOG_DIR = Path(os.getenv("LOG_DIR", DATA_ROOT / "logs"))
LOG_ROTATION = os.getenv("LOG_ROTATION", "10 MB")
LOG_RETENTION = os.getenv("LOG_RETENTION", "14 days")

CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | {message}"
)


class InterceptHandler(logging.Handler):
    """Forward standard-library logs, including Uvicorn logs, to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 0
        while frame is not None and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    """Configure console/file logging and route framework logs through Loguru."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=CONSOLE_FORMAT,
        colorize=True,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        LOG_DIR / "backend-{time:YYYY-MM-DD}.log",
        level=LOG_LEVEL,
        format=FILE_FORMAT,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    intercept_handler = InterceptHandler()
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        standard_logger = logging.getLogger(logger_name)
        standard_logger.handlers = [intercept_handler]
        standard_logger.propagate = False

    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)
    logger.info(
        "Logging initialized level={} directory={} rotation={} retention={}",
        LOG_LEVEL,
        LOG_DIR,
        LOG_ROTATION,
        LOG_RETENTION,
    )


