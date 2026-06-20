"""Tests for LLM context packer, verifier, and API endpoints (Phase 1)."""

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import app
from llm_config import llm_enabled
from llm_context import build_context_pack
from llm_verifier import verify_context_pack
from quality_profiles import PROFILES, assess_profile, build_contract_rules, evaluate_rule
from profiler import profile_dataframe

client = TestClient(app)

SURVEY_CSV = b"""respondent_id,q1,q2,q3
R1,5,5,5
R1,5,5,5
R2,3,,4
R3,,,
R4,1,2,3
"""


@pytest.fixture(autouse=True)
def mock_llm_provider(monkeypatch):
    monkeypatch.setenv("DATALENS_LLM_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _upload_survey(content: bytes = SURVEY_CSV, required: str = "respondent_id"):
    files = {"file": ("survey.csv", io.BytesIO(content), "text/csv")}
    data = {"quality_profile": "survey", "required_columns": required}
    return client.post("/api/upload", files=files, data=data)


def test_survey_contract_rules_include_unique_respondent_and_missingness():
    df = pd.read_csv(io.BytesIO(SURVEY_CSV))
    profiles, _ = profile_dataframe(df)
    rules = build_contract_rules(df, PROFILES["survey"], ["respondent_id"])
    ids = {r.id for r in rules}
    assert "unique_respondent" in ids
    assert "high_item_missingness" in ids

    unique_rule = next(r for r in rules if r.id == "unique_respondent")
    result = evaluate_rule(df, unique_rule)
    assert result["passed"] is False
    assert result["violation_count"] >= 2

    miss_rule = next(r for r in rules if r.id == "high_item_missingness")
    miss_result = evaluate_rule(df, miss_rule)
    assert miss_result["passed"] is False


def test_context_pack_is_bounded_and_excludes_full_data():
    df = pd.read_csv(io.BytesIO(SURVEY_CSV))
    profiles, qs = profile_dataframe(df)
    session = {
        "df": df,
        "df_full": df,
        "profiles": profiles,
        "quality_score": qs,
        "filename": "survey.csv",
        "revision": 1,
        "quality_profile_id": "survey",
        "profile_assessment": assess_profile(df, profiles, "survey", ["respondent_id"]),
        "row_sample_limit": None,
    }
    pack = build_context_pack(session, "test-session")
    assert pack["quality_profile_id"] == "survey"
    assert pack["row_count_analyzed"] == len(df)
    assert "samples" in pack
    assert "constraints" in pack
    assert "valid_fix_types" in pack["constraints"]
    total_sample_rows = sum(len(v) for v in pack["samples"].values())
    assert total_sample_rows <= 5 * max(len(pack["rules_failed"]), 1)


def test_mock_verifier_returns_structured_result():
    df = pd.read_csv(io.BytesIO(SURVEY_CSV))
    profiles, _ = profile_dataframe(df)
    session = {
        "df": df,
        "df_full": df,
        "profiles": profiles,
        "quality_score": profile_dataframe(df)[1],
        "filename": "survey.csv",
        "revision": 1,
        "quality_profile_id": "survey",
        "profile_assessment": assess_profile(df, profiles, "survey", ["respondent_id"]),
        "row_sample_limit": None,
    }
    pack = build_context_pack(session, "sid")
    result = verify_context_pack(pack)
    assert result.model_id
    assert isinstance(result.confirmed_issues, list)
    assert result.verification_confidence >= 0


def test_llm_verify_endpoint_stores_and_revision_invalidation():
    assert llm_enabled()
    r = _upload_survey()
    assert r.status_code == 200
    body = r.json()
    sid = body["session_id"]
    assert body.get("llm_available") is True

    verify = client.post(f"/api/session/{sid}/llm/verify")
    assert verify.status_code == 200
    vbody = verify.json()
    assert vbody["llm_verification"] is not None
    assert len(vbody["llm_verification"]["confirmed_issues"]) >= 1
    assert vbody["llm_verification_stale"] is False
    rev_after_verify = vbody["revision"]

    get_v = client.get(f"/api/session/{sid}/llm/verification")
    assert get_v.status_code == 200
    assert get_v.json()["verification"] is not None

    fix = client.post(
        "/api/fixes",
        json={"session_id": sid, "fixes": {"q1": "drop_nulls"}},
    )
    assert fix.status_code == 200
    fbody = fix.json()
    assert fbody["revision"] == rev_after_verify + 1
    assert fbody["llm_verification_stale"] is True


def test_llm_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("DATALENS_LLM_PROVIDER", "none")
    r = _upload_survey()
    sid = r.json()["session_id"]
    verify = client.post(f"/api/session/{sid}/llm/verify")
    assert verify.status_code == 503


def test_health_includes_llm_status():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "llm" in r.json()
