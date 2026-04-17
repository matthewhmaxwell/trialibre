"""Tests for the API key authentication middleware."""

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from ctm.api.app import create_app
from ctm.config import load_settings


@pytest.fixture
def app_with_auth(tmp_path):
    settings = load_settings()
    settings.database.sqlite_path = str(tmp_path / "test.db")
    settings.api.api_keys = ["secret-key-abc123", "another-valid-key"]
    return create_app(settings=settings)


@pytest.fixture
def app_without_auth(tmp_path):
    settings = load_settings()
    settings.database.sqlite_path = str(tmp_path / "test.db")
    settings.api.api_keys = []  # Empty = auth disabled
    return create_app(settings=settings)


class TestAuthDisabled:
    async def test_no_key_required_when_unconfigured(self, app_without_auth):
        async with LifespanManager(app_without_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_without_auth), base_url="http://t"
            ) as c:
                r = await c.get("/api/v1/sandbox/protocols")
                assert r.status_code == 200


class TestAuthEnabled:
    async def test_health_is_public(self, app_with_auth):
        """Health check must remain public for load balancer probes."""
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.get("/api/v1/health")
                assert r.status_code == 200

    async def test_unauthenticated_request_rejected(self, app_with_auth):
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.get("/api/v1/sandbox/protocols")
                assert r.status_code == 401
                assert "API key required" in r.json()["detail"]

    async def test_invalid_key_rejected(self, app_with_auth):
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.get(
                    "/api/v1/sandbox/protocols",
                    headers={"X-API-Key": "wrong-key"},
                )
                assert r.status_code == 403

    async def test_valid_key_header_accepted(self, app_with_auth):
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.get(
                    "/api/v1/sandbox/protocols",
                    headers={"X-API-Key": "secret-key-abc123"},
                )
                assert r.status_code == 200

    async def test_valid_key_query_param_accepted(self, app_with_auth):
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.get("/api/v1/sandbox/protocols?api_key=secret-key-abc123")
                assert r.status_code == 200

    async def test_either_configured_key_works(self, app_with_auth):
        """Multiple keys can be configured for key rotation."""
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.get(
                    "/api/v1/sandbox/protocols",
                    headers={"X-API-Key": "another-valid-key"},
                )
                assert r.status_code == 200

    async def test_post_endpoint_also_protected(self, app_with_auth):
        async with LifespanManager(app_with_auth):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_auth), base_url="http://t"
            ) as c:
                r = await c.post("/api/v1/match", json={"patient_text": "test"})
                assert r.status_code == 401
