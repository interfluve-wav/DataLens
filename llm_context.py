"""
Context packer — converts profiler/session output into a bounded LLM prompt payload.

The LLM never receives the full dataset; only summaries, rule outcomes, and capped
sample rows that Python already computed deterministically.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from hardening import VALID_FIX_TYPES
from llm_config import llm_max_sample_rows
from profiler import ColumnProfile
from quality_profiles import empty_cells_per_row


def _serialize_column_for_pack(p: ColumnProfile, max_top: int = 5) -> Dict[str, Any]:
    top = (p.top_values or [])[:max_top]
    return {
        "name": p.name,
        "dtype": p.dtype,
        "null_pct": round(p.null_pct, 2),
        "unique_count": p.unique_count,
        "mixed_type_pct": round(p.mixed_type_pct, 2),
        "issues": list(p.issues),
        "recommendations": list(p.recommendations),
        "top_values": [[str(v), int(c)] for v, c in top],
    }


def _columns_of_interest(
    profiles: List[ColumnProfile],
    rules_failed: List[Dict[str, Any]],
    limit: int = 12,
) -> List[Dict[str, Any]]:
    names: List[str] = []
    for rule in rules_failed:
        for col in rule.get("columns") or []:
            if col not in names:
                names.append(col)
    for p in sorted(profiles, key=lambda x: (-x.null_pct, -x.mixed_type_pct)):
        if p.issues and p.name not in names:
            names.append(p.name)
        if len(names) >= limit:
            break
    by_name = {p.name: p for p in profiles}
    return [_serialize_column_for_pack(by_name[n]) for n in names[:limit] if n in by_name]


def _cap_samples(
    rules: List[Dict[str, Any]], max_rows: int
) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for rule in rules:
        if not rule.get("passed", True):
            samples = rule.get("sample_failures") or []
            out[rule["rule_id"]] = samples[:max_rows]
    return out


def _row_completeness_summary(df: pd.DataFrame, top_n: int = 5) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    counts = empty_cells_per_row(df)
    hist = counts.value_counts().sort_index()
    return [
        {"nulls_in_row": int(k), "row_count": int(v)}
        for k, v in hist.head(top_n).items()
    ]


def _issue_counts(profiles: List[ColumnProfile]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "nulls": 0,
        "outliers": 0,
        "mixed_types": 0,
        "email": 0,
        "encoding": 0,
        "whitespace": 0,
        "date_format": 0,
    }
    for p in profiles:
        if p.null_pct > 0:
            counts["nulls"] += 1
        if p.mixed_type_pct > 5:
            counts["mixed_types"] += 1
        if p.outlier_pct > 5:
            counts["outliers"] += 1
        if (p.invalid_email_count or 0) > 0:
            counts["email"] += 1
        if (p.encoding_issues or 0) > 0:
            counts["encoding"] += 1
        if (p.whitespace_count or 0) > 0:
            counts["whitespace"] += 1
        if p.date_format_count >= 2:
            counts["date_format"] += 1
    return counts


def build_context_pack(session: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Build a bounded JSON context for the LLM verifier.

    Uses the working (possibly sampled) frame for column profiles and the full frame
    for row-completeness stats when available.
    """
    df_work: pd.DataFrame = session["df"]
    df_full: pd.DataFrame = session.get("df_full", df_work)
    profiles: List[ColumnProfile] = session["profiles"]
    pa: Optional[Dict[str, Any]] = session.get("profile_assessment")
    max_rows = llm_max_sample_rows()
    limit = session.get("row_sample_limit")
    is_sampled = limit is not None and limit < len(df_full)

    rules = list(pa.get("rules", [])) if pa else []
    rules_failed = [r for r in rules if not r.get("passed")]
    rules_passed = [r for r in rules if r.get("passed")]

    pack: Dict[str, Any] = {
        "session_id": session_id,
        "revision": session.get("revision", 1),
        "filename": session.get("filename", "upload.dat"),
        "quality_profile_id": session.get("quality_profile_id", "generic"),
        "profile_label": pa.get("profile_label") if pa else "Generic",
        "profile_source": pa.get("source") if pa else "",
        "is_sampled": is_sampled,
        "row_count_analyzed": len(df_work),
        "total_row_count": len(df_full),
        "dimension_scores": pa.get("dimension_scores", []) if pa else [],
        "rules_failed": [
            {
                "rule_id": r["rule_id"],
                "name": r["name"],
                "severity": r["severity"],
                "message": r["message"],
                "violation_count": r["violation_count"],
                "violation_pct": r["violation_pct"],
            }
            for r in rules_failed
        ],
        "rules_passed_count": len(rules_passed),
        "columns_of_interest": _columns_of_interest(profiles, rules_failed),
        "samples": _cap_samples(rules, max_rows),
        "row_completeness": _row_completeness_summary(df_full),
        "issue_summary": _issue_counts(profiles),
        "constraints": {
            "valid_fix_types": sorted(VALID_FIX_TYPES),
            "max_rows_cited": max_rows,
            "note": "Respond only from evidence in this pack; do not invent rows or counts.",
        },
    }

    return pack
