"""Tests for the FastAPI endpoints."""

import tempfile
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from ctm.api.app import create_app
from ctm.config import load_settings


def _has_nltk_punkt():
    try:
        import nltk
        nltk.data.find("tokenizers/punkt_tab")
        return True
    except (LookupError, ImportError):
        return False


needs_nltk = pytest.mark.skipif(not _has_nltk_punkt(), reason="NLTK punkt_tab data not available")


@pytest.fixture
def app(tmp_path):
    """Create a test app with an isolated SQLite database."""
    settings = load_settings()
    db_file = tmp_path / "test.db"
    settings.database.sqlite_path = str(db_file)
    return create_app(settings=settings)


@pytest.fixture
async def client(app):
    """AsyncClient that also runs the lifespan context (DB connect/disconnect)."""
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class TestHealthEndpoint:
    async def test_health(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "sandbox_mode" in data


class TestSandboxEndpoints:
    @needs_nltk
    async def test_list_patients(self, client):
        resp = await client.get("/api/v1/sandbox/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_list_protocols(self, client):
        resp = await client.get("/api/v1/sandbox/protocols")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_list_scenarios(self, client):
        resp = await client.get("/api/v1/sandbox/scenarios")
        assert resp.status_code == 200


class TestPrivacyEndpoint:
    async def test_privacy_status(self, client):
        resp = await client.get("/api/v1/privacy/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "label" in data
        assert "color" in data


class TestMatchEndpoint:
    @needs_nltk
    async def test_match_sandbox(self, client):
        resp = await client.post("/api/v1/match", json={
            "patient_text": "45 year old female with Type 2 diabetes, HbA1c 8.2%",
            "max_trials": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data
        assert data["sandbox_mode"] is True
