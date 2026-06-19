"""Regression tests for drift detection and row completeness consistency."""

import io

import pandas as pd

from api import _row_completeness_hist
from profiler import detect_schema_drift, load_csv, apply_fixes, profile_dataframe
from quality_profiles import build_contract_rules, evaluate_rule, PROFILES


def test_schema_drift_detects_distribution_shift_on_string_csv():
    baseline = pd.read_csv(
        io.BytesIO(b"value\n" + b"\n".join(str(i).encode() for i in range(50))),
        dtype=str,
    )
    shifted = pd.read_csv(
        io.BytesIO(b"value\n" + b"\n".join(str(i + 100).encode() for i in range(50))),
        dtype=str,
    )
    drift = detect_schema_drift(baseline, shifted)
    assert len(drift.distribution_shifted) >= 1


def test_row_completeness_treats_nan_string_as_empty():
    df = pd.DataFrame({"a": ["ok", "nan", None], "b": ["x", "y", "z"]})
    hist = _row_completeness_hist(df)
    one_null = next(r for r in hist if r["nulls_in_row"] == 1)
    assert one_null["row_count"] == 2  # literal "nan" and None


def test_strip_whitespace_does_not_turn_null_into_nan_string():
    df = pd.DataFrame({"name": ["  alice  ", None]})
    profiles, _ = profile_dataframe(pd.read_csv(
        io.BytesIO(b"name\n  alice  \n"), dtype=str
    ))
    fixed = apply_fixes(df, profiles, {"name": "strip_whitespace"})
    assert fixed["name"].iloc[0] == "alice"
    assert pd.isna(fixed["name"].iloc[1])
