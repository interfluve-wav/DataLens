"""Regression tests for analytics helpers used on every upload."""

import io

import pandas as pd

from api import _analytics_bundle, _issue_summary, _row_completeness_hist
from profiler import profile_dataframe


def test_row_completeness_hist_handles_dataframe_not_series():
    """Must not call .str on a DataFrame (pandas AttributeError on upload)."""
    df = pd.DataFrame(
        {
            "a": [1, None, "  "],
            "b": ["x", "", "y"],
            "c": [10, 20, 30],
        }
    )
    result = _row_completeness_hist(df)
    assert isinstance(result, list)
    assert all("nulls_in_row" in row and "row_count" in row for row in result)
    total_rows = sum(r["row_count"] for r in result)
    assert total_rows == len(df)


def test_row_completeness_hist_empty_frame():
    assert _row_completeness_hist(pd.DataFrame()) == []


def test_analytics_bundle_includes_row_completeness():
    df = pd.read_csv(io.BytesIO(b"name,score\nalice,1\nbob,\n"), dtype=str)
    profiles, qs = profile_dataframe(df)
    issues = _issue_summary(profiles)
    bundle = _analytics_bundle(df, profiles, qs, {"columns": [], "matrix": []}, issues)
    assert "row_completeness" in bundle
    assert isinstance(bundle["row_completeness"], list)
