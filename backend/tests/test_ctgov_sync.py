"""Tests for the bulk CT.gov sync endpoint.

The CT.gov client is monkeypatched to return canned results so tests
don't depend on network connectivity or registry stability.
"""

from __future__ import annotations

import asyncio

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from ctm.api.app import create_app
from ctm.config import load_settings
from ctm.models.trial import ClinicalTrial, EligibilityCriteria


def _make_trial(nct: str, title: str = "Test Trial") -> ClinicalTrial:
    return ClinicalTrial(
        nct_id=nct,
        brief_title=title,
        diseases=["Test Condition"],
        inclusion_criteria=[
            EligibilityCriteria(index=0, text="Adult", category="inclusion"),
        ],
        exclusion_criteria=[
            EligibilityCriteria(index=0, text="Pregnant", category="exclusion"),
        ],
        source_registry="ctgov",
    )


@pytest.fixture
def app(tmp_path):
    settings = load_settings()
    settings.database.sqlite_path = str(tmp_path / "test.db")
    return create_app(settings=settings)


@pytest.fixture
def mock_ctgov(monkeypatch):
    """Replace CTGovClient.search with a canned response generator.

    Returns a `pages` list — push dicts to control what each successive
    `search()` call returns.
    """
    pages: list[dict] = []
    closed = False

    async def fake_search(self, **kwargs):
        if not pages:
            return {"trials": [], "total": 0, "next_page_token": None}
        return pages.pop(0)

    async def fake_close(self):
        nonlocal closed
        closed = True

    monkeypatch.setattr(
        "ctm.data.registries.ctgov_client.CTGovClient.search",
        fake_search,
    )
    monkeypatch.setattr(
        "ctm.data.registries.ctgov_client.CTGovClient.close",
        fake_close,
    )
    return pages


async def _wait_for_status(client, job_id: str, target: str, timeout: float = 5.0) -> dict:
    """Poll the sync status until it matches `target` or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    last = None
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"/api/v1/ingest/ctgov-sync/{job_id}")
        last = r.json()
        if last["status"] == target:
            return last
        await asyncio.sleep(0.05)
    return last


class TestSyncEndpoint:
    async def test_sync_requires_at_least_one_filter(self, app, mock_ctgov):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/api/v1/ingest/ctgov-sync", json={})
                assert r.status_code == 400
                assert "at least one filter" in r.json()["detail"]

    async def test_sync_returns_job_id_immediately(self, app, mock_ctgov):
        # Push a single empty page so the background task finishes quickly
        mock_ctgov.append({"trials": [], "total": 0, "next_page_token": None})

        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={"condition": "diabetes", "max_trials": 10},
                )
                assert r.status_code == 200
                body = r.json()
                assert "job_id" in body
                assert body["status"] == "running"

    async def test_sync_imports_trials_from_single_page(self, app, mock_ctgov):
        mock_ctgov.append({
            "trials": [_make_trial("NCT00000001"), _make_trial("NCT00000002")],
            "total": 2,
            "next_page_token": None,
        })

        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={"condition": "diabetes", "max_trials": 10},
                )
                job_id = r.json()["job_id"]

                final = await _wait_for_status(c, job_id, "completed")
                assert final["status"] == "completed"
                assert final["completed"] == 2
                assert final["failed"] == 0
                assert final["total"] == 2

                # Verify the trials are now in the trials list
                r = await c.get("/api/v1/trials?limit=200")
                ctgov_trials = [t for t in r.json()["trials"] if t["source"] == "ctgov"]
                ids = {t["nct_id"] for t in ctgov_trials}
                assert "NCT00000001" in ids
                assert "NCT00000002" in ids

    async def test_sync_paginates_through_multiple_pages(self, app, mock_ctgov):
        mock_ctgov.append({
            "trials": [_make_trial(f"NCT0000010{i}") for i in range(3)],
            "total": 5,
            "next_page_token": "page2",
        })
        mock_ctgov.append({
            "trials": [_make_trial(f"NCT0000020{i}") for i in range(2)],
            "total": 5,
            "next_page_token": None,
        })

        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={"condition": "diabetes", "max_trials": 10, "page_size": 100},
                )
                job_id = r.json()["job_id"]

                final = await _wait_for_status(c, job_id, "completed")
                assert final["completed"] == 5
                assert final["total"] == 5

    async def test_sync_respects_max_trials_cap(self, app, mock_ctgov):
        # API claims 1000 trials available; we cap at 5
        mock_ctgov.append({
            "trials": [_make_trial(f"NCT0000030{i}") for i in range(10)],
            "total": 1000,
            "next_page_token": "more",
        })

        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={"condition": "cancer", "max_trials": 5},
                )
                job_id = r.json()["job_id"]
                final = await _wait_for_status(c, job_id, "completed")
                # Should stop at exactly 5 even though page had 10
                assert final["completed"] == 5
                assert final["total"] == 5  # capped from 1000 → 5

    async def test_sync_records_metadata(self, app, mock_ctgov):
        mock_ctgov.append({"trials": [], "total": 0, "next_page_token": None})

        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={
                        "condition": "diabetes",
                        "phase": ["PHASE3"],
                        "max_trials": 100,
                    },
                )
                job_id = r.json()["job_id"]
                final = await _wait_for_status(c, job_id, "completed")
                assert final["metadata"]["condition"] == "diabetes"
                assert final["metadata"]["phase"] == ["PHASE3"]
                assert final["metadata"]["max_trials"] == 100

    async def test_get_sync_status_404(self, app, mock_ctgov):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.get("/api/v1/ingest/ctgov-sync/nonexistent")
                assert r.status_code == 404

    async def test_get_sync_status_rejects_match_jobs(self, app, mock_ctgov):
        """The sync status endpoint should reject jobs that aren't sync jobs."""
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # Create a regular match batch job
                r = await c.post("/api/v1/batch", json={
                    "patients": [{"patient_id": "P1", "text": "test patient with diabetes"}],
                })
                match_job_id = r.json()["job_id"]
                # Try to fetch it via the sync endpoint
                r = await c.get(f"/api/v1/ingest/ctgov-sync/{match_job_id}")
                assert r.status_code == 400
                assert "not a CT.gov sync job" in r.json()["detail"]

    async def test_validation_max_trials_too_high(self, app, mock_ctgov):
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={"condition": "diabetes", "max_trials": 100_000},
                )
                assert r.status_code == 422

    async def test_sync_handles_search_failure(self, app, monkeypatch):
        """If CT.gov search itself raises, the job should be marked failed."""
        async def failing_search(self, **kwargs):
            raise RuntimeError("CT.gov is down")

        async def fake_close(self):
            pass

        monkeypatch.setattr(
            "ctm.data.registries.ctgov_client.CTGovClient.search",
            failing_search,
        )
        monkeypatch.setattr(
            "ctm.data.registries.ctgov_client.CTGovClient.close",
            fake_close,
        )

        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post(
                    "/api/v1/ingest/ctgov-sync",
                    json={"condition": "diabetes"},
                )
                job_id = r.json()["job_id"]
                final = await _wait_for_status(c, job_id, "failed")
                assert final["status"] == "failed"
                assert any("CT.gov is down" in str(item.get("error", ""))
                           for item in final["results"])
