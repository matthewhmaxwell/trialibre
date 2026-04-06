"""Tests for the privacy engine."""

from ctm.privacy.engine import PrivacyEngine
from ctm.config import load_settings


class TestPrivacyEngine:
    def test_create(self, settings):
        engine = PrivacyEngine(settings)
        assert engine is not None

    def test_status_cloud_with_deid(self):
        """Cloud LLM with de-ID active should show 'Secure'."""
        settings = load_settings()
        # Default is Anthropic (cloud) with de-ID on
        engine = PrivacyEngine(settings)
        if settings.is_cloud_llm:
            assert engine.is_active is True
            status = engine.get_status()
            assert status["label"] == "Secure"
            assert status["color"] == "blue"
            assert status["deid_active"] is True

    def test_status_local(self):
        """Local LLM should show 'Private' status."""
        settings = load_settings()
        settings.llm.provider = "ollama"
        engine = PrivacyEngine(settings)
        assert engine.is_active is False
        status = engine.get_status()
        assert status["label"] == "Private"
        assert status["color"] == "green"
        assert status["deid_active"] is False

    def test_status_has_required_fields(self, settings):
        """Status dict should have all fields the UI needs."""
        engine = PrivacyEngine(settings)
        status = engine.get_status()
        assert "label" in status
        assert "color" in status
        assert "details" in status
        assert "deid_active" in status
        assert "processing_location" in status
        assert isinstance(status["details"], list)
