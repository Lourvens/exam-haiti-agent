"""Tests configuration module."""

import os
from pathlib import Path

import pytest


class TestConfig:
    """Test configuration module."""

    def test_settings_loads_defaults(self):
        """Test that default settings load correctly."""
        from app.config import settings

        assert settings.app_name == "Exam Haiti Agent"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.api_prefix == "/api/v1"

    def test_settings_llm_defaults(self):
        """Test LLM default settings."""
        from app.config import settings

        assert settings.llm_provider == "openai"
        assert settings.openai_model == "gpt-4o-mini"
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.embedding_dimensions == 1536

    def test_settings_chroma_defaults(self):
        """Test Chroma default settings."""
        from app.config import settings

        assert settings.chroma_collection_name == "exam_chunks"
        assert settings.chroma_persist_directory == Path("data/chroma")

    def test_settings_chunking_defaults(self):
        """Test chunking default settings."""
        from app.config import settings

        assert settings.chunk_max_tokens == 1000
        assert settings.chunk_overlap_tokens == 100

    def test_settings_logging_defaults(self):
        """Test logging default settings."""
        from app.config import settings

        assert settings.log_directory == Path("logs")
        assert settings.log_level == "INFO"
        assert settings.log_rotation == "1 day"
        assert settings.log_retention == "30 days"

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns cached instance."""
        from app.config import get_settings, settings

        result = get_settings()
        assert result is settings
