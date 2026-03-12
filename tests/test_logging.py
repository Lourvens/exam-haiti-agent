"""Tests logging configuration."""

import os
from pathlib import Path

import pytest


class TestLogging:
    """Test logging configuration."""

    def test_setup_logging_creates_logs_directory(self):
        """Test that setup_logging creates logs directory."""
        from logs_config.config import setup_logging

        setup_logging()
        log_dir = Path("logs").resolve()
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_setup_logging_creates_log_files(self):
        """Test that log files are created."""
        from logs_config.config import setup_logging

        setup_logging()
        log_dir = Path("logs").resolve()

        expected_files = ["app.log", "api.log", "rag.log", "errors.log"]
        for filename in expected_files:
            log_file = log_dir / filename
            assert log_file.exists(), f"{filename} should exist"

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger."""
        from logs_config.config import get_logger

        logger = get_logger("test")
        assert logger is not None

    def test_get_logger_with_context(self):
        """Test logger with context."""
        from logs_config.config import get_logger

        logger = get_logger("test", request_id="123", endpoint="/test")
        assert logger is not None
