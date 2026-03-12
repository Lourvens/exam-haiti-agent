"""Tests FastAPI application."""

import pytest
from httpx import ASGITransport, AsyncClient


class TestFastAPI:
    """Test FastAPI application."""

    @pytest.fixture
    def app(self):
        """Get FastAPI app."""
        from app.main import app
        return app

    @pytest.mark.asyncio
    async def test_root_endpoint(self, app):
        """Test root endpoint returns correct data."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Exam Haiti Agent"
            assert data["version"] == "0.1.0"
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, app):
        """Test health endpoint returns healthy."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_app_has_cors_configured(self, app):
        """Test CORS middleware is configured."""
        # Check that CORS middleware is in the app
        cors_middleware = None
        for middleware in app.user_middleware:
            if hasattr(middleware, "cls") and middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break
        assert cors_middleware is not None, "CORS middleware should be configured"
