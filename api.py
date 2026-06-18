"""
DataLens API — FastAPI backend for the React frontend.
Wraps profiler.py with JSON-serializable responses.
"""

from __future__ import annotations

import base64
import io
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from profiler import (
    ColumnProfile,
    QualityLevel,
    QualityScore,
    SchemaDrift,
    apply_fixes,
    detect_schema_drift,
    generate_markdown_report,
    load_csv,
    profile_dataframe,
)

app = FastAPI(title="DataLens API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (single-user dev; replace with Redis for production)
_sessions: Dict[str, Dict[str, Any]] = {}


def _enum_val(v: Any) -> Any:
    if isinstance(v, Enum):
        return v.value
    return v


def _serialize_profile(p: ColumnProfile) -> Dict[str, Any]:
    d = asdict(p)
    d["quality_level"] = p.quality_level.value
    return d


def _serialize_quality(qs: QualityScore) -> Dict[str, Any]:
    return {
        "overall": qs.overall,
        "level": qs.level.value,
        "breakdown": qs.breakdown,
        "column_scores": qs.column_scores,
    }


def _serialize_drift(drift: SchemaDrift) -> Dict[str, Any]:
    return {
        "added_columns": drift.added_columns,
        "removed_columns": drift.removed_columns,
        "type_changed": [
            {"column": c, "from": old, "to": new}
            for c, old, new in drift.type_changed
        ],
        "distribution_shifted": [
            {"column": c, "p_value": p} for c, p in drift.distribution_shifted
        ],
        "summary": drift.summary,
    }


def _df_preview(df: pd.DataFrame, limit: int = 50) -> List[Dict[str, Any]]:
    preview = df.head(limit).fillna("").astype(str)
    return preview.to_dict(orient="records")


def _column_series(df: pd.DataFrame, col: str) -> List[Any]:
    """Return column values for charting (numeric where possible)."""
    series = df[col]
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() / max(len(series), 1) > 0.6:
        return [float(x) if pd.notna(x) else None for x in numeric.tolist()]
    return [str(x) if pd.notna(x) else None for x in series.tolist()]


def _correlation_matrix(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_df = df.apply(pd.to_numeric, errors="coerce")
    numeric_cols = [c for c in numeric_df.columns if numeric_df[c].notna().sum() > 10]
    if len(numeric_cols) < 2:
        return {"columns": [], "matrix": []}
    corr = numeric_df[numeric_cols].corr().fillna(0)
    return {
        "columns": numeric_cols,
        "matrix": corr.values.tolist(),
    }


def _null_matrix(profiles: List[ColumnProfile]) -> List[Dict[str, Any]]:
    return [
        {
            "column": p.name,
            "null_pct": p.null_pct,
            "dtype": p.dtype,
            "quality": p.quality_score,
        }
        for p in profiles
    ]


def _issue_summary(profiles: List[ColumnProfile]) -> Dict[str, int]:
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
        if p.outlier_pct > 0:
            counts["outliers"] += 1
        if p.mixed_type_pct > 5:
            counts["mixed_types"] += 1
        if p.invalid_email_count > 0:
            counts["email"] += 1
        if p.encoding_issues > 0:
            counts["encoding"] += 1
        if p.whitespace_count > 0:
            counts["whitespace"] += 1
        if p.date_format_count >= 2:
            counts["date_format"] += 1
    return counts


def _best_correlation_pair(corr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    columns = corr.get("columns", [])
    matrix = corr.get("matrix", [])
    if len(columns) < 2:
        return None
    best_i, best_j, best_r = 0, 1, 0.0
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            r = abs(matrix[i][j])
            if r > abs(best_r):
                best_i, best_j, best_r = i, j, matrix[i][j]
    return {"x_col": columns[best_i], "y_col": columns[best_j], "r": best_r}


def _scatter_points(
    df: pd.DataFrame, x_col: str, y_col: str, limit: int = 800
) -> List[Dict[str, float]]:
    x = pd.to_numeric(df[x_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    mask = x.notna() & y.notna()
    paired = pd.DataFrame({"x": x[mask], "y": y[mask]})
    if len(paired) > limit:
        paired = paired.sample(n=limit, random_state=42)
    return [{"x": float(r.x), "y": float(r.y)} for r in paired.itertuples()]


def _box_plot_stats(df: pd.DataFrame, col: str) -> Optional[Dict[str, Any]]:
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(series) < 5:
        return None
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = series[(series < lower) | (series > upper)]
    return {
        "column": col,
        "min": float(series.min()),
        "q1": q1,
        "median": float(series.median()),
        "q3": q3,
        "max": float(series.max()),
        "outliers": int(len(outliers)),
    }


def _row_completeness_hist(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Histogram of how many null/empty values each row has."""
    # .str is Series-only; see tests/test_api_analytics.py
    stripped = df.astype(str).apply(lambda col: col.str.strip())
    empty = df.isna() | (stripped == "")
    nulls_per_row = empty.sum(axis=1)
    if len(nulls_per_row) == 0:
        return []
    counts = nulls_per_row.value_counts().sort_index()
    return [
        {"nulls_in_row": int(k), "row_count": int(v)}
        for k, v in counts.items()
    ]


def _analytics_bundle(
    df: pd.DataFrame,
    profiles: List[ColumnProfile],
    qs: QualityScore,
    corr: Dict[str, Any],
    issues: Dict[str, int],
) -> Dict[str, Any]:
    dtype_counts: Dict[str, int] = {}
    for p in profiles:
        dtype_counts[p.dtype] = dtype_counts.get(p.dtype, 0) + 1

    null_sorted = sorted(profiles, key=lambda p: p.null_pct, reverse=True)[:15]
    quality_sorted = sorted(profiles, key=lambda p: p.quality_score)

    numeric_profiles = [p for p in profiles if p.dtype == "numeric"]
    box_plots = []
    for p in sorted(
        numeric_profiles,
        key=lambda x: x.outlier_pct + x.null_pct,
        reverse=True,
    )[:8]:
        stats = _box_plot_stats(df, p.name)
        if stats:
            box_plots.append(stats)

    pair = _best_correlation_pair(corr)
    scatter = None
    if pair:
        scatter = {
            **pair,
            "points": _scatter_points(df, pair["x_col"], pair["y_col"]),
        }

    penalties = [
        {"name": k.replace("_", " ").title(), "penalty": round(v, 2)}
        for k, v in qs.breakdown.items()
        if v > 0.05
    ]

    issue_mix = [
        {"name": k.replace("_", " ").title(), "count": v}
        for k, v in issues.items()
        if v > 0
    ]

    numeric_null = [p for p in profiles if p.dtype == "numeric"]
    avg_outlier = (
        sum(p.outlier_pct for p in numeric_null) / len(numeric_null)
        if numeric_null
        else 0.0
    )
    avg_null = sum(p.null_pct for p in profiles) / max(len(profiles), 1)
    dup_penalty = qs.breakdown.get("duplicates", 0)

    health_radar = [
        {
            "metric": "Completeness",
            "score": max(0, 100 - avg_null),
        },
        {
            "metric": "Outliers",
            "score": max(0, 100 - avg_outlier),
        },
        {
            "metric": "Uniqueness",
            "score": max(0, 100 - dup_penalty * 5),
        },
        {
            "metric": "Types",
            "score": max(0, 100 - qs.breakdown.get("type_mismatch", 0) * 6),
        },
        {
            "metric": "Cardinality",
            "score": max(0, 100 - qs.breakdown.get("low_cardinality", 0) * 8),
        },
        {
            "metric": "Deep checks",
            "score": max(0, 100 - qs.breakdown.get("deep_issues", 0) * 8),
        },
    ]

    stacked_null = [
        {
            "column": p.name[:20],
            "valid": round(100 - p.null_pct, 1),
            "null": round(p.null_pct, 1),
        }
        for p in null_sorted[:10]
        if p.null_pct > 0
    ]

    cat_top = []
    for p in profiles:
        if p.dtype == "categorical" and p.top_values:
            for val, cnt in p.top_values[:3]:
                cat_top.append(
                    {
                        "label": f"{p.name}: {str(val)[:16]}",
                        "count": cnt,
                    }
                )
    cat_top.sort(key=lambda x: x["count"], reverse=True)
    cat_top = cat_top[:12]

    return {
        "dtype_mix": [
            {"name": k.title(), "value": v} for k, v in dtype_counts.items()
        ],
        "null_by_column": [
            {"column": p.name, "null_pct": round(p.null_pct, 2)}
            for p in null_sorted
        ],
        "quality_ranking": [
            {"column": p.name, "score": round(p.quality_score, 1)}
            for p in quality_sorted
        ],
        "penalty_breakdown": penalties,
        "issue_mix": issue_mix,
        "scatter": scatter,
        "box_plots": box_plots,
        "row_completeness": _row_completeness_hist(df),
        "health_radar": health_radar,
        "stacked_null": stacked_null,
        "top_categories": cat_top,
    }


def _working_df(session: Dict[str, Any]) -> pd.DataFrame:
    """Return the active dataframe, optionally row-sampled."""
    full: pd.DataFrame = session.get("df_full", session["df"])
    limit = session.get("row_sample_limit")
    if limit is not None and limit < len(full):
        return full.sample(n=int(limit), random_state=42).reset_index(drop=True)
    return full


def _reprofile_session(session: Dict[str, Any]) -> None:
    """Re-profile the working (possibly sampled) dataframe."""
    df = _working_df(session)
    profiles, qs = profile_dataframe(df)
    session["df"] = df
    session["profiles"] = profiles
    session["quality_score"] = qs
    if session.get("baseline_df") is not None:
        session["schema_drift"] = detect_schema_drift(session["baseline_df"], df)


def _session_payload(session: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    if "df_full" not in session:
        session["df_full"] = session["df"]

    df: pd.DataFrame = session["df"]
    df_full: pd.DataFrame = session["df_full"]
    profiles: List[ColumnProfile] = session["profiles"]
    qs: QualityScore = session["quality_score"]
    corr = _correlation_matrix(df)
    issues = _issue_summary(profiles)
    limit = session.get("row_sample_limit")

    return {
        "session_id": session_id,
        "filename": session["filename"],
        "row_count": len(df),
        "total_row_count": len(df_full),
        "row_sample_limit": limit,
        "is_sampled": limit is not None and limit < len(df_full),
        "column_count": len(df.columns),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "profiles": [_serialize_profile(p) for p in profiles],
        "quality_score": _serialize_quality(qs),
        "schema_drift": (
            _serialize_drift(session["schema_drift"])
            if session.get("schema_drift")
            else None
        ),
        "preview": _df_preview(df),
        "correlation": corr,
        "null_matrix": _null_matrix(profiles),
        "issue_summary": issues,
        "analytics": _analytics_bundle(df, profiles, qs, corr, issues),
        "applied_fixes": session.get("applied_fixes", {}),
    }


class ApplyFixesRequest(BaseModel):
    session_id: str
    fixes: Dict[str, str]


class DriftRequest(BaseModel):
    session_id: str


class SampleRequest(BaseModel):
    session_id: str
    row_limit: Optional[int] = None  # None = all rows


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "datalens"}


@app.post("/api/upload")
async def upload_csv(
    file: UploadFile = File(...),
    baseline: Optional[UploadFile] = File(None),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file")

    try:
        content = await file.read()
        df = load_csv(content)
        profiles, qs = profile_dataframe(df)
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse CSV: {exc}") from exc

    session_id = base64.urlsafe_b64encode(file.filename.encode()).decode()[:32]
    session: Dict[str, Any] = {
        "filename": file.filename,
        "df_full": df,
        "df": df,
        "row_sample_limit": None,
        "profiles": profiles,
        "quality_score": qs,
        "baseline_df": None,
        "schema_drift": None,
        "applied_fixes": {},
    }

    if baseline is not None:
        try:
            baseline_bytes = await baseline.read()
            session["baseline_df"] = load_csv(baseline_bytes)
            session["schema_drift"] = detect_schema_drift(session["baseline_df"], df)
        except Exception as exc:
            raise HTTPException(400, f"Failed to parse baseline CSV: {exc}") from exc

    _sessions[session_id] = session

    payload = _session_payload(session, session_id)
    payload["schema_drift"] = (
        _serialize_drift(session["schema_drift"])
        if session["schema_drift"]
        else None
    )
    return payload


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return _session_payload(session, session_id)


@app.get("/api/session/{session_id}/column/{column_name}")
def get_column_data(session_id: str, column_name: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    df: pd.DataFrame = session["df"]
    if column_name not in df.columns:
        raise HTTPException(404, f"Column '{column_name}' not found")

    profile = next(
        (p for p in session["profiles"] if p.name == column_name),
        None,
    )
    if not profile:
        raise HTTPException(404, "Profile not found")

    values = _column_series(df, column_name)
    numeric_vals = [v for v in values if isinstance(v, (int, float)) and v is not None]

    histogram: Optional[Dict[str, Any]] = None
    if numeric_vals and profile.dtype == "numeric":
        import numpy as np

        counts, bins = np.histogram(numeric_vals, bins=30)
        histogram = {
            "bins": [float(b) for b in bins[:-1]],
            "counts": [int(c) for c in counts],
        }

    return {
        "column": column_name,
        "profile": _serialize_profile(profile),
        "values": values[:5000],
        "histogram": histogram,
        "top_values": profile.top_values or [],
    }


@app.post("/api/drift")
def compute_drift(req: DriftRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session["baseline_df"] is None:
        raise HTTPException(400, "No baseline uploaded")

    drift = detect_schema_drift(session["baseline_df"], session["df"])
    session["schema_drift"] = drift
    return _serialize_drift(drift)


@app.post("/api/fixes")
def apply_fixes_endpoint(req: ApplyFixesRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if not req.fixes:
        raise HTTPException(400, "No fixes specified")

    try:
        fixed_df = apply_fixes(
            session.get("df_full", session["df"]),
            session["profiles"],
            req.fixes,
        )
        session["df_full"] = fixed_df
        session["applied_fixes"].update(req.fixes)
        _reprofile_session(session)
    except Exception as exc:
        raise HTTPException(400, f"Failed to apply fixes: {exc}") from exc

    return _session_payload(session, req.session_id)


@app.post("/api/sample")
def set_row_sample(req: SampleRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if "df_full" not in session:
        session["df_full"] = session["df"]

    full_len = len(session["df_full"])
    if req.row_limit is not None:
        if req.row_limit < 1:
            raise HTTPException(400, "row_limit must be at least 1")
        if req.row_limit >= full_len:
            session["row_sample_limit"] = None
        else:
            session["row_sample_limit"] = int(req.row_limit)
    else:
        session["row_sample_limit"] = None

    _reprofile_session(session)
    return _session_payload(session, req.session_id)


@app.get("/api/session/{session_id}/report")
def get_report(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    report = generate_markdown_report(
        session["profiles"],
        session["quality_score"],
        session.get("schema_drift"),
        filename=session["filename"],
    )
    return {"markdown": report, "filename": f"datalens_{session['filename']}_report.md"}
