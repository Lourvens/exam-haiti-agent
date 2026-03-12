"""Custom logging handlers."""

import sys
from typing import Any

from loguru import logger


class APIFormatter:
    """Formatter for API-specific logs."""

    def format(self, record: dict[str, Any]) -> str:
        """Format log record for API."""
        extra = record.get("extra", {})
        request_id = extra.get("request_id", "-")
        endpoint = extra.get("endpoint", "-")

        return (
            f"[{record['time']}] [{record['level']}] "
            f"[req:{request_id}] [{endpoint}] - {record['message']}"
        )


class RAGFormatter:
    """Formatter for RAG-specific logs."""

    def format(self, record: dict[str, Any]) -> str:
        """Format log record for RAG."""
        extra = record.get("extra", {})
        query = extra.get("query", "-")[:50]
        node = extra.get("node", "-")

        return (
            f"[{record['time']}] [{record['level']}] "
            f"[node:{node}] [query:{query}] - {record['message']}"
        )


# Re-export logger for convenience
__all__ = ["logger", "APIFormatter", "RAGFormatter"]
