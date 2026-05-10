"""Tests for the /feedback endpoint.

Three contracts pinned:
1. POST /feedback persists a row and returns the canonical record shape.
2. The verdict's score context (combined_score, strength, criteria
   counts) survives the round trip — required for later drift analysis
   when comparing the same (patient, trial) across model upgrades.
3. Validation: only the {correct, incorrect, unsure} feedback types
   are accepted; anything else is a 422.
"""

from __future__ import annotations

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport

from ctm.api.app import create_app
from ctm.config import load_settings


@pytest.fixture
def app(tmp_path):
    settings = load_settings()
    settings.database.sqlite_path = str(tmp_path / "test.db")
    return create_app(settings=settings)


async def test_post_feedback_persists_and_round_trips(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t"
        ) as c:
            payload = {
                "patient_id": "P-001",
                "trial_id": "NCT-001",
                "feedback_type": "incorrect",
                "notes": "Patient is pediatric; trial is adult-only.",
                "data": {
                    "strength": "possible",
                    "combined_score": 0.47,
                    "criteria_met": 5,
                },
            }
            r = await c.post("/api/v1/feedback", json=payload)
            assert r.status_code == 201, r.text
            row = r.json()
            assert row["patient_id"] == "P-001"
            assert row["trial_id"] == "NCT-001"
            assert row["feedback_type"] == "incorrect"
            assert row["notes"] == payload["notes"]
            # Score context survives the round trip (data fields get
            # spread into the dict by the repo).
            assert row["combined_score"] == 0.47

            # GET list endpoint returns it.
            r = await c.get("/api/v1/feedback")
            assert r.status_code == 200
            rows = r.json()
            assert len(rows) == 1
            assert rows[0]["feedback_id"] == row["feedback_id"]


async def test_aggregate_returns_counts_and_agreement_rate(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t"
        ) as c:
            base = {"patient_id": "P", "trial_id": "T"}
            for verdict in ("correct", "correct", "correct", "incorrect", "unsure"):
                r = await c.post(
                    "/api/v1/feedback",
                    json={**base, "feedback_type": verdict},
                )
                assert r.status_code == 201

            r = await c.get("/api/v1/feedback/aggregate")
            assert r.status_code == 200
            agg = r.json()
            assert agg["total"] == 5
            assert agg["counts"] == {"correct": 3, "incorrect": 1, "unsure": 1}
            assert agg["agreement_rate"] == pytest.approx(0.6)


async def test_invalid_feedback_type_is_422(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t"
        ) as c:
            r = await c.post(
                "/api/v1/feedback",
                json={
                    "patient_id": "P",
                    "trial_id": "T",
                    "feedback_type": "definitely-yes",
                },
            )
            assert r.status_code == 422
            assert "feedback_type" in r.text


async def test_aggregate_returns_null_rate_when_empty(app):
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t"
        ) as c:
            r = await c.get("/api/v1/feedback/aggregate")
            assert r.status_code == 200
            assert r.json() == {
                "total": 0,
                "counts": {"correct": 0, "incorrect": 0, "unsure": 0},
                "agreement_rate": None,
            }
