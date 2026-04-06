"""Tests for language detection."""

from ctm.i18n.language_detector import detect_language


class TestLanguageDetection:
    def test_detect_english(self):
        lang = detect_language("Patient presents with chest pain and shortness of breath. History of hypertension and diabetes mellitus.")
        assert lang == "en"

    def test_detect_portuguese(self):
        lang = detect_language("O paciente apresenta dor torácica e falta de ar. Histórico de hipertensão arterial e diabetes mellitus diagnosticados há três anos.")
        assert lang == "pt"

    def test_detect_spanish(self):
        lang = detect_language("El paciente presenta dolor torácico y dificultad para respirar. Antecedentes de hipertensión arterial y diabetes mellitus.")
        assert lang == "es"

    def test_detect_french(self):
        lang = detect_language("Le patient présente une douleur thoracique et un essoufflement. Antécédents d'hypertension artérielle et de diabète sucré.")
        assert lang == "fr"

    def test_detect_short_text_returns_string(self):
        lang = detect_language("HbA1c 8.2%")
        assert isinstance(lang, str)
        assert len(lang) >= 2
