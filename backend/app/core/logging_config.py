"""
Production-ready structured logging configuration using loguru.
"""

import logging
import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings

class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages toward Loguru sinks.
    See: https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging() -> None:
    """Configure Loguru for console and file logging."""
    
    # Remove default loguru handler
    logger.remove()

    # Define log format
    # Example: 2026-06-29 18:00:12 | INFO | User uploaded resume
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"

    log_level = "DEBUG" if settings.DEBUG else "INFO"

    # 1. Console Logging
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
    )

    # 2. File Logging
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_dir / "resumesh_{time}.log"),
        format=log_format,
        level=log_level,
        rotation="500 MB",       # Rotate when file reaches 500MB
        retention="10 days",     # Keep logs for 10 days
        compression="zip",       # Zip rotated logs
        enqueue=True,            # Thread-safe async logging
    )

    # Intercept standard library logging (e.g., Uvicorn, FastAPI, SQLAlchemy)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Suppress noisy loggers from standard library
    for noisy_logger in ["uvicorn.access", "sqlalchemy.engine", "httpx"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logger.info("Logging configured successfully.")
