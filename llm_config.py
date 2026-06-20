"""LLM integration configuration (Phase 1 verifier)."""

from __future__ import annotations

import os

VALID_LLM_PROVIDERS = frozenset({"none", "mock", "openai"})


def llm_provider() -> str:
    raw = os.environ.get("DATALENS_LLM_PROVIDER", "none").strip().lower()
    return raw if raw in VALID_LLM_PROVIDERS else "none"


def llm_enabled() -> bool:
    provider = llm_provider()
    if provider == "none":
        return False
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())
    return provider == "mock"


def llm_model() -> str:
    return os.environ.get("DATALENS_LLM_MODEL", "gpt-4o-mini")


def llm_max_sample_rows() -> int:
    return max(1, int(os.environ.get("DATALENS_LLM_MAX_SAMPLE_ROWS", "5")))


def llm_status() -> dict:
    provider = llm_provider()
    enabled = llm_enabled()
    return {
        "enabled": enabled,
        "provider": provider if enabled else "none",
        "model": llm_model() if provider == "openai" and enabled else None,
    }
