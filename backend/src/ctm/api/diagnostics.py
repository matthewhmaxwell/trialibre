"""Runtime environment diagnostics.

Checks which optional features are actually available in the current
deployment and returns human-readable warnings for things that are
misconfigured or missing. Used by `/health` so the UI can surface them.
"""

from __future__ import annotations

import shutil


def check_capabilities() -> dict[str, bool]:
    """Detect which optional capabilities are present in the runtime.

    Returns a dict of capability_name -> available. Checks are lightweight
    (no subprocess calls) and safe to run on every /health request.
    """
    return {
        "ocr": shutil.which("tesseract") is not None,
        "weasyprint": _module_available("weasyprint"),
        "presidio": _module_available("presidio_analyzer"),
        "faiss": _module_available("faiss"),
        "curl": shutil.which("curl") is not None,
    }


def warnings_from_state(settings, llm, capabilities: dict[str, bool]) -> list[str]:
    """Generate user-visible warnings based on runtime state."""
    warnings: list[str] = []

    # LLM configured but didn't initialize
    if llm is None and settings.llm.provider.value != "ollama":
        if settings.llm.api_key:
            warnings.append(
                f"An {settings.llm.provider.value} API key is configured but the "
                "provider failed to initialize. Check the server logs. Matching is "
                "using sandbox data until this is resolved."
            )
        elif not settings.sandbox.enabled:
            warnings.append(
                f"No API key is configured for {settings.llm.provider.value}. "
                "Set the CTM_LLM__API_KEY environment variable or enable sandbox mode."
            )

    # Ollama configured but probably not reachable
    if settings.llm.provider.value == "ollama" and llm is None:
        warnings.append(
            f"Ollama is selected as the provider but the server at "
            f"{getattr(settings.llm, 'base_url', 'localhost:11434')} is not reachable. "
            "Matching is using sandbox data. Install Ollama and pull a model, or "
            "switch providers in Settings."
        )

    # OCR unavailable
    if not capabilities.get("ocr"):
        warnings.append(
            "Tesseract is not installed. Photo/image patient input will return "
            "empty text. Install with `brew install tesseract` (macOS) or "
            "`apt install tesseract-ocr` (Linux)."
        )

    # PDF report generation unavailable
    if not capabilities.get("weasyprint"):
        warnings.append(
            "WeasyPrint is not fully installed. PDF referral reports may fail. "
            "Install system dependencies: pango, cairo, gdk-pixbuf."
        )

    # De-ID unavailable but privacy level expects it
    if not capabilities.get("presidio") and settings.privacy.deid_mode.value != "off":
        warnings.append(
            "Presidio is not installed but de-identification is enabled. "
            "Patient data will NOT be de-identified before LLM calls. "
            "Install with `pip install presidio-analyzer presidio-anonymizer`."
        )

    # Sandbox mode is on when user didn't explicitly enable it
    if settings.sandbox.enabled and llm is None:
        warnings.append(
            "Running in sandbox mode. Results are pre-computed from sample data, "
            "not live AI matching. Configure an AI provider to match real patients."
        )

    return warnings


def _module_available(module_name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(module_name) is not None
