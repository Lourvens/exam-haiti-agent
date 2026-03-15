"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Optional, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra fields in .env
    )

    # ===============================
    # App
    # ===============================
    app_name: str = "Exam Haiti Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # ===============================
    # API
    # ===============================
    api_prefix: str = "/api/v1"

    # ===============================
    # LLM Configuration
    # ===============================
    llm_provider: str = "openai"

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_api_base: Optional[str] = Field(default=None, validation_alias="OPENAI_API_BASE")

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"

    # Google
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.0-flash"

    # ===============================
    # Embeddings Configuration
    # ===============================
    embedding_provider: Literal["auto", "openai", "huggingface"] = "auto"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # HuggingFace
    hf_token: Optional[str] = Field(default=None, validation_alias="HF_TOKEN")
    hf_api_key: Optional[str] = Field(default=None, validation_alias="HF_API_KEY")
    hf_embedding_model: Optional[str] = Field(default=None, validation_alias="HF_EMBEDDING_MODEL")

    # Override defaults
    openai_embedding_model: Optional[str] = Field(default=None, validation_alias="OPENAI_EMBEDDING_MODEL")

    # ===============================
    # Chroma Vector Store
    # ===============================
    chroma_persist_directory: Path = Path("data/chroma")
    chroma_collection_name: str = "exam_chunks"

    # ===============================
    # Chunking
    # ===============================
    chunk_max_tokens: int = 1000
    chunk_overlap_tokens: int = 100

    # ===============================
    # Storage
    # ===============================
    pdf_storage_path: Path = Path("data/pdfs")

    # ===============================
    # Logging
    # ===============================
    log_directory: Path = Path("logs")
    log_level: str = "INFO"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"

    # ===============================
    # Computed Properties
    # ===============================
    @property
    def effective_embedding_provider(self) -> Literal["openai", "huggingface"]:
        """Get the effective embedding provider based on available credentials."""
        # If explicitly set, use that
        if self.embedding_provider != "auto":
            return self.embedding_provider

        # Check available credentials
        if self.openai_api_key:
            return "openai"
        if self.hf_token or self.hf_api_key:
            return "huggingface"

        raise ValueError(
            "No embedding provider available. Set one of:\n"
            "  - OPENAI_API_KEY for OpenAI embeddings\n"
            "  - HF_TOKEN for HuggingFace embeddings"
        )

    @property
    def effective_embedding_model(self) -> str:
        """Get the effective embedding model based on provider."""
        provider = self.effective_embedding_provider

        if provider == "openai":
            return self.openai_embedding_model or self.embedding_model
        else:  # huggingface
            return self.hf_embedding_model or "sentence-transformers/all-MiniLM-L6-v2"

    @property
    def has_llm_provider(self) -> bool:
        """Check if LLM provider credentials are available."""
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        elif self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        elif self.llm_provider == "google":
            return bool(self.google_api_key)
        return False

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def validate_openai_key(cls, v):
        """Validate OpenAI API key."""
        # Allow None, will be checked when needed
        return v

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        """Validate overall configuration."""
        # Ensure at least LLM or embeddings can work
        if not self.has_llm_provider:
            # Only warn, not all features may need LLM
            pass

        return self


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
