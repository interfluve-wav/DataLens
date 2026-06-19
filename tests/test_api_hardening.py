"""API hardening: session IDs, limits, drift on full data, fix validation."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

import api
import hardening
from api import app

client = TestClient(app)

SAMPLE = b"""store_id,date,sku,sales
1,2024-06-01,A,100
2,2024-06-02,B,200
3,2024-06-03,C,150
4,2024-06-04,D,250
5,2024-06-05,E,300
"""


def _upload(content: bytes = SAMPLE, filename: str = "test.csv") -> dict:
    r = client.post(
        "/api/upload",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
        data={"quality_profile": "generic"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_session_ids_are_unique():
    ids = {_upload()["session_id"] for _ in range(5)}
    assert len(ids) == 5


def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(hardening, "MAX_UPLOAD_BYTES", 50)
    r = client.post(
        "/api/upload",
        files={"file": ("big.csv", io.BytesIO(SAMPLE), "text/csv")},
        data={"quality_profile": "generic"},
    )
    assert r.status_code == 413


def test_drift_uses_full_data_after_sample(monkeypatch):
    baseline = b"value\n" + b"\n".join(str(i).encode() for i in range(80))
    current = b"value\n" + b"\n".join(str(i + 50).encode() for i in range(80))

    r = client.post(
        "/api/upload",
        files={
            "file": ("current.csv", io.BytesIO(current), "text/csv"),
            "baseline": ("baseline.csv", io.BytesIO(baseline), "text/csv"),
        },
        data={"quality_profile": "generic"},
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]

    r = client.post("/api/sample", json={"session_id": sid, "row_limit": 3})
    assert r.status_code == 200
    assert r.json()["is_sampled"] is True

    drift = client.post("/api/drift", json={"session_id": sid}).json()
    assert drift["summary"]
    assert any(
        item.get("column") == "value" for item in drift.get("distribution_shifted", [])
    )


def test_unknown_fix_type_rejected():
    sid = _upload()["session_id"]
    r = client.post(
        "/api/fixes",
        json={"session_id": sid, "fixes": {"sales": "magic_fix"}},
    )
    assert r.status_code == 400
    assert "Unknown fix type" in r.json()["detail"]


def test_unknown_column_rejected():
    sid = _upload()["session_id"]
    r = client.post(
        "/api/fixes",
        json={"session_id": sid, "fixes": {"missing_col": "drop_nulls"}},
    )
    assert r.status_code == 400
    assert "Unknown column" in r.json()["detail"]


def test_baseline_load_failure_returns_400(monkeypatch):
    real_load = api._load_file_dataset
    calls = {"n": 0}

    def load_side_effect(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_load(*args, **kwargs)
        raise RuntimeError("network down")

    monkeypatch.setattr(api, "_load_file_dataset", load_side_effect)

    r = client.post(
        "/api/upload",
        files={
            "file": ("test.csv", io.BytesIO(SAMPLE), "text/csv"),
            "baseline": ("baseline.csv", io.BytesIO(SAMPLE), "text/csv"),
        },
        data={"quality_profile": "generic"},
    )
    assert r.status_code == 400
    assert "baseline" in r.json()["detail"].lower()


def test_too_many_rows_rejected(monkeypatch):
    monkeypatch.setattr(hardening, "MAX_ROWS", 2)
    r = client.post(
        "/api/upload",
        files={"file": ("test.csv", io.BytesIO(SAMPLE), "text/csv")},
        data={"quality_profile": "generic"},
    )
    assert r.status_code == 400
    assert "Too many rows" in r.json()["detail"]
