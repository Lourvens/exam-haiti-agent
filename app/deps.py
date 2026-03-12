"""FastAPI dependencies."""

from functools import lru_cache

from app.config import Settings, get_settings


@lru_cache
def get_cached_settings() -> Settings:
    """Get cached settings instance."""
    return get_settings()
