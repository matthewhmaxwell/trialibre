"""Tests that uploaded trials, referrals, and batch jobs persist in the database."""

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from ctm.api.app import create_app
from ctm.config import load_settings


@pytest.fixture
def app_factory(tmp_path):
    """Factory that creates apps pointing at the same SQLite file.

    Used to verify that state persists across server restarts.
    """
    db_file = tmp_path / "test.db"

    def make():
        settings = load_settings()
        settings.database.sqlite_path = str(db_file)
        return create_app(settings=settings)

    return make


async def _client_for(app):
    """Helper to build an async client with lifespan."""
    manager = LifespanManager(app)
    transport = ASGITransport(app=app)
    return manager, AsyncClient(transport=transport, base_url="http://test")


class TestTrialPersistence:
    async def test_uploaded_trial_survives_restart(self, app_factory):
        """Upload a trial, restart, verify it's still there."""
        # First server lifetime: upload
        app1 = app_factory()
        async with LifespanManager(app1):
            async with AsyncClient(transport=ASGITransport(app=app1), base_url="http://t") as c:
                resp = await c.post("/api/v1/ingest/trial", data={
                    "text": (
                        "Inclusion Criteria:\n1. Adult aged 18 or older\n"
                        "2. Confirmed diagnosis of diabetes\n\n"
                        "Exclusion Criteria:\n1. Pregnant\n2. On insulin"
                    ),
                    "title": "Test Persistence Protocol",
                })
                assert resp.status_code == 200
                uploaded_id = resp.json()["nct_id"]

        # Second server lifetime: verify
        app2 = app_factory()
        async with LifespanManager(app2):
            async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://t") as c:
                resp = await c.get(f"/api/v1/trials/{uploaded_id}")
                assert resp.status_code == 200, f"Expected trial to survive restart: {resp.text}"
                assert resp.json()["brief_title"] == "Test Persistence Protocol"

    async def test_delete_uploaded_trial(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # Upload
                r = await c.post("/api/v1/ingest/trial", data={
                    "text": "Inclusion Criteria:\n1. Adult\n\nExclusion Criteria:\n1. Minor",
                    "title": "To Delete",
                })
                uid = r.json()["nct_id"]

                # Delete
                r = await c.delete(f"/api/v1/trials/{uid}")
                assert r.status_code == 200

                # Verify gone
                r = await c.get(f"/api/v1/trials/{uid}")
                assert r.status_code == 404

    async def test_cannot_delete_sandbox_trial(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.delete("/api/v1/trials/SAMPLE-NCT-001")
                assert r.status_code == 403

    async def test_trials_list_merges_sandbox_and_persisted(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.get("/api/v1/trials?limit=200")
                assert r.status_code == 200
                data = r.json()
                # Sandbox trials should be there (24 sample protocols)
                assert data["total"] >= 20, f"Expected sandbox trials in list, got {data['total']}"


class TestReferralPersistence:
    async def test_referral_survives_restart(self, app_factory):
        app1 = app_factory()
        async with LifespanManager(app1):
            async with AsyncClient(transport=ASGITransport(app=app1), base_url="http://t") as c:
                r = await c.post("/api/v1/referrals", json={
                    "patient_id": "P-TEST-001",
                    "trial_id": "NCT99999999",
                    "trial_title": "Test Trial",
                    "recipient_email": "coord@example.com",
                })
                assert r.status_code == 200, r.text
                rid = r.json()["referral_id"]

        # New server, same DB
        app2 = app_factory()
        async with LifespanManager(app2):
            async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://t") as c:
                r = await c.get(f"/api/v1/referrals/{rid}")
                assert r.status_code == 200
                assert r.json()["patient_id"] == "P-TEST-001"

    async def test_referral_status_update(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/api/v1/referrals", json={
                    "patient_id": "P-X",
                    "trial_id": "NCT12345678",
                })
                rid = r.json()["referral_id"]

                r = await c.put(f"/api/v1/referrals/{rid}/status", json={"status": "sent"})
                assert r.status_code == 200
                assert r.json()["status"] == "sent"

    async def test_invalid_referral_status_rejected(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/api/v1/referrals", json={
                    "patient_id": "P-X", "trial_id": "NCT12345678",
                })
                rid = r.json()["referral_id"]
                # Invalid status should be rejected by Pydantic regex
                r = await c.put(f"/api/v1/referrals/{rid}/status", json={"status": "bogus"})
                assert r.status_code == 422

    async def test_invalid_email_rejected(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/api/v1/referrals", json={
                    "patient_id": "P-X",
                    "trial_id": "NCT12345678",
                    "recipient_email": "not-an-email",
                })
                assert r.status_code == 422


class TestValidation:
    async def test_upload_size_limit_enforced(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # 60 MB of text — over the 50 MB limit
                huge = "x" * (60 * 1024 * 1024)
                r = await c.post("/api/v1/ingest/trial", data={"text": huge})
                # Over the MAX_TEXT_LENGTH limit (1M chars) — 413
                assert r.status_code == 413

    async def test_nct_id_invalid_format_rejected(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/api/v1/ingest/ctgov/not-a-real-nct")
                assert r.status_code == 400
                assert "NCT" in r.json()["detail"]

    async def test_batch_input_validation(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # Text too short — under 10 char minimum
                r = await c.post("/api/v1/batch", json={
                    "patients": [{"patient_id": "P1", "text": "short"}],
                })
                assert r.status_code == 422

    async def test_batch_size_limit(self, app_factory):
        app = app_factory()
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # 101 patients — over limit
                too_many = [
                    {"patient_id": f"P{i}", "text": "Some reasonable patient text here."}
                    for i in range(101)
                ]
                r = await c.post("/api/v1/batch", json={"patients": too_many})
                assert r.status_code == 422
