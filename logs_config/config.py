"""Logging configuration using loguru."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    """Configure loguru with file and console handlers."""
    # Remove default handler
    logger.remove()

    # Log format
    log_format = (
        "<green>[{time:YYYY-MM-DD HH:mm:ss}]</green> "
        "<level>[{level}]</level> "
        "<cyan>[{name}:{function}:{line}]</cyan> - "
        "<level>{message}</level>"
    )

    # Console handler (INFO and above)
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    # Ensure log directory exists (absolute path)
    log_dir = Path("logs").resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    # Main app log
    logger.add(
        log_dir / "app.log",
        format=log_format,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        serialize=True,
    )

    # API log
    logger.add(
        log_dir / "api.log",
        format=log_format,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        serialize=True,
    )

    # RAG log
    logger.add(
        log_dir / "rag.log",
        format=log_format,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        serialize=True,
    )

    # Errors log (WARNING and above)
    logger.add(
        log_dir / "errors.log",
        format=log_format,
        level="WARNING",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        serialize=True,
    )


def get_logger(name: str | None = None, **kwargs: Any):
    """Get a logger instance with optional context."""
    if name:
        return logger.bind(name=name, **kwargs)
    return logger.bind(**kwargs)
