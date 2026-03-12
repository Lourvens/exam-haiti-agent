"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Exam Haiti Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # API
    api_prefix: str = "/api/v1"

    # LLM Configuration
    llm_provider: str = "openai"  # openai, anthropic, google, ollama
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.0-flash"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Chroma
    chroma_persist_directory: Path = Path("data/chroma")
    chroma_collection_name: str = "exam_chunks"

    # Chunking
    chunk_max_tokens: int = 1000
    chunk_overlap_tokens: int = 100

    # Storage
    pdf_storage_path: Path = Path("data/pdfs")

    # Logging
    log_directory: Path = Path("logs")
    log_level: str = "INFO"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"


settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
