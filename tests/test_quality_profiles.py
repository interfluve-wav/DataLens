"""Unit tests for sector profiles and DQ contract evaluation."""

import io

import pandas as pd

from profiler import profile_dataframe
from quality_profiles import (
    PROFILES,
    assess_profile,
    build_contract_rules,
    evaluate_rule,
    list_profiles,
    resolve_profile_columns,
)


def test_list_profiles_includes_generic_and_retail():
    profiles = list_profiles()
    ids = {p["id"] for p in profiles}
    assert "generic" in ids
    assert "retail" in ids
    assert all("weights" in p and "dimensions" in p for p in profiles)


def test_not_null_rule_fails_on_empty_values():
    df = pd.DataFrame({"sku": ["A", "", None, "B"]})
    rule = build_contract_rules(df, PROFILES["generic"], ["sku"])[1]
    result = evaluate_rule(df, rule)
    assert result["passed"] is False
    assert result["violation_count"] == 2


def test_unique_composite_key_rule():
    df = pd.DataFrame(
        {
            "store_id": [1, 1, 2],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "sku": ["X", "X", "Y"],
        }
    )
    rules = build_contract_rules(df, PROFILES["retail"], ["store_id", "date", "sku"])
    unique_rule = next(r for r in rules if r.rule_type == "unique")
    result = evaluate_rule(df, unique_rule)
    assert result["passed"] is False
    assert result["violation_count"] == 2


def test_min_value_rule_negative_sales():
    df = pd.DataFrame({"sales": [10.0, -1.0, 5.0]})
    rules = build_contract_rules(df, PROFILES["retail"], [])
    sales_rule = next(r for r in rules if r.rule_type == "min_value")
    result = evaluate_rule(df, sales_rule)
    assert result["passed"] is False
    assert result["violation_count"] == 1


def test_assess_profile_retail_weighted_score():
    csv = io.BytesIO(
        b"store_id,date,sku,sales\n"
        b"1,2024-06-01,A,100\n"
        b"2,2024-06-02,B,200\n"
        b"3,2024-06-03,C,150\n"
    )
    df = pd.read_csv(csv, dtype=str)
    profiles, _ = profile_dataframe(df)
    assessment = assess_profile(df, profiles, "retail")
    assert assessment["profile_id"] == "retail"
    assert 0 <= assessment["overall"] <= 100
    assert assessment["rules_total"] >= 1
    assert assessment["contract_passed"] is True
    assert len(assessment["dimension_scores"]) == len(PROFILES["retail"].weights)


def test_user_required_columns_missing():
    df = pd.DataFrame({"a": [1, 2]})
    required, missing = resolve_profile_columns(
        df, PROFILES["generic"], user_required=["a", "missing_col"]
    )
    assert required == ["a"]
    assert missing == ["missing_col"]
