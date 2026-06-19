"""
Upload every on-disk file format twice.

Run fixture generation first:
  python tests/scripts/generate_format_fixtures.py
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# (filename, optional sheet_name, min_rows expected)
UPLOAD_CASES = [
    ("retail_sample.csv", None, 3),
    ("retail_sample.tsv", None, 3),
    ("retail_sample.txt", None, 3),
    ("retail_sample.json", None, 3),
    ("retail_sample.parquet", None, 3),
    ("retail_sample.xlsx", None, 3),
    ("retail_sample.xlsx", "Archive", 1),
    ("retail_sample.xlsm", None, 3),
    ("retail_sample.ods", None, 3),
    ("sales_records_100.csv", None, 50),
    ("sales_records_100.xlsx", None, 50),
    ("sales_records_100.parquet", None, 50),
    ("sales_records_100.json", None, 50),
]


def _fixture_path(name: str) -> Path:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"Missing fixture {name}; run tests/scripts/generate_format_fixtures.py")
    return path


def _upload_file(path: Path, sheet_name: str | None = None):
    data = {"quality_profile": "retail", "required_columns": "store_id,date,sku,sales"}
    if sheet_name:
        data["sheet_name"] = sheet_name
    # sales_records uses different columns — use generic profile
    if path.name.startswith("sales_records"):
        data = {"quality_profile": "generic"}

    with path.open("rb") as fh:
        files = {"file": (path.name, fh, "application/octet-stream")}
        return client.post("/api/upload", files=files, data=data)


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures():
    script = Path(__file__).resolve().parent / "scripts" / "generate_format_fixtures.py"
    if not (FIXTURES / "retail_sample.csv").exists() and script.exists():
        import subprocess
        import sys

        subprocess.run([sys.executable, str(script)], check=True, cwd=FIXTURES.parents[1])


@pytest.mark.parametrize("filename,sheet_name,min_rows", UPLOAD_CASES)
def test_upload_format_pass_1(filename: str, sheet_name: str | None, min_rows: int):
    path = _fixture_path(filename)
    r = _upload_file(path, sheet_name)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] >= min_rows
    assert body["column_count"] >= 1
    assert body["quality_score"]["overall"] >= 0
    assert body["analytics"] is not None
    if sheet_name:
        assert body.get("sheet_name") == sheet_name


@pytest.mark.parametrize("filename,sheet_name,min_rows", UPLOAD_CASES)
def test_upload_format_pass_2(filename: str, sheet_name: str | None, min_rows: int):
    """Second pass — same fixtures, verify stable responses."""
    path = _fixture_path(filename)
    r = _upload_file(path, sheet_name)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] >= min_rows
    assert "profile_assessment" in body
    assert body["profiles"]


def test_inspect_multi_sheet_workbook():
    path = _fixture_path("retail_sample.xlsx")
    with path.open("rb") as fh:
        r = client.post(
            "/api/inspect",
            files={"file": (path.name, fh, "application/octet-stream")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["has_sheets"] is True
    assert set(body["sheets"]) == {"Retail", "Archive"}


def test_formats_endpoint_lists_parquet_and_excel():
    r = client.get("/api/formats")
    assert r.status_code == 200
    exts = {f["extension"] for f in r.json()["formats"]}
    assert {".parquet", ".xlsx", ".json", ".csv", ".ods"} <= exts
