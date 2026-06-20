"""
Sector quality profiles, weighted dimension scoring, and data-quality contracts.

Weights are adapted from published frameworks (noted per profile). Dimension scores
are 0–100 where higher is better; overall = weighted sum of dimensions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from profiler import ColumnProfile, QualityLevel


@dataclass(frozen=True)
class ProfileDefinition:
    id: str
    label: str
    description: str
    source: str
    weights: Dict[str, float]
    column_hints: Dict[str, List[str]] = field(default_factory=dict)


PROFILES: Dict[str, ProfileDefinition] = {
    "generic": ProfileDefinition(
        id="generic",
        label="Generic CSV",
        description="Balanced hygiene scoring for any tabular dataset.",
        source="DataLens default (aligned with README penalty weights).",
        weights={
            "completeness": 0.25,
            "uniqueness": 0.20,
            "outliers": 0.20,
            "type_consistency": 0.15,
            "cardinality": 0.10,
            "deep_checks": 0.10,
        },
    ),
    "retail": ProfileDefinition(
        id="retail",
        label="Retail / Transactional",
        description="Keys, sales facts, and duplicate transaction detection.",
        source="TCS DQART retail; Wang & Strong fitness-for-use.",
        weights={
            "completeness": 0.25,
            "uniqueness": 0.20,
            "timeliness": 0.15,
            "validity": 0.15,
            "type_consistency": 0.10,
            "outliers": 0.15,
        },
        column_hints={
            "store_id": ["store_id", "store", "location_id", "store_nbr"],
            "date": ["date", "dt", "transaction_date", "week"],
            "sku": ["sku", "item_id", "product_id", "item"],
            "sales": ["sales", "revenue", "amount", "weekly_sales"],
        },
    ),
    "healthcare": ProfileDefinition(
        id="healthcare",
        label="Healthcare / Clinical",
        description="Completeness and consistency for clinical or claims data.",
        source="Al-Hgaish et al. AHP on ISO 25012; Kahn et al. EHR framework.",
        weights={
            "completeness": 0.21,
            "validity": 0.16,
            "type_consistency": 0.14,
            "timeliness": 0.15,
            "precision": 0.14,
            "deep_checks": 0.10,
            "uniqueness": 0.10,
        },
        column_hints={
            "patient_id": ["patient_id", "member_id", "mrn", "subject_id"],
            "event_date": ["date", "event_date", "service_date", "admit_date"],
        },
    ),
    "financial": ProfileDefinition(
        id="financial",
        label="Financial / KYC",
        description="Timeliness, integrity, and compliance-oriented checks.",
        source="Li et al. Future Internet 2023 (trust institution AHP weights).",
        weights={
            "timeliness": 0.36,
            "completeness": 0.23,
            "validity": 0.13,
            "compliance": 0.11,
            "type_consistency": 0.08,
            "uniqueness": 0.09,
        },
        column_hints={
            "customer_id": ["customer_id", "client_id", "account_id", "cif"],
            "email": ["email", "email_address"],
        },
    ),
    "survey": ProfileDefinition(
        id="survey",
        label="Survey / Research",
        description="Item-level completeness and duplicate respondent detection.",
        source="AAPOR Standard Definitions; Total Survey Error framework.",
        weights={
            "completeness": 0.25,
            "uniqueness": 0.25,
            "validity": 0.25,
            "type_consistency": 0.15,
            "deep_checks": 0.10,
        },
        column_hints={
            "respondent_id": ["respondent_id", "response_id", "id", "uuid"],
        },
    ),
    "ml_training": ProfileDefinition(
        id="ml_training",
        label="ML Training",
        description="Labels, feature completeness, and duplicate row detection.",
        source="Gong et al. dataset quality survey; ML training DQ practice.",
        weights={
            "label_quality": 0.25,
            "completeness": 0.20,
            "uniqueness": 0.15,
            "type_consistency": 0.15,
            "outliers": 0.15,
            "validity": 0.10,
        },
        column_hints={
            "label": ["label", "target", "y", "class"],
        },
    ),
}


def list_profiles() -> List[Dict[str, Any]]:
    return [
        {
            "id": p.id,
            "label": p.label,
            "description": p.description,
            "source": p.source,
            "weights": p.weights,
            "dimensions": list(p.weights.keys()),
        }
        for p in PROFILES.values()
    ]


def _level_from_score(score: float) -> QualityLevel:
    if score >= 90:
        return QualityLevel.EXCELLENT
    if score >= 70:
        return QualityLevel.GOOD
    if score >= 50:
        return QualityLevel.NEEDS_CLEANING
    return QualityLevel.POOR


def _resolve_column(df: pd.DataFrame, hints: Sequence[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in df.columns}
    for hint in hints:
        if hint.lower() in lower_map:
            return lower_map[hint.lower()]
    return None


def resolve_profile_columns(
    df: pd.DataFrame,
    profile: ProfileDefinition,
    user_required: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Return (resolved_required, missing_hints)."""
    resolved: List[str] = []
    missing: List[str] = []

    if user_required:
        for col in user_required:
            col = col.strip()
            if not col:
                continue
            if col in df.columns:
                if col not in resolved:
                    resolved.append(col)
            else:
                missing.append(col)
        return resolved, missing

    for role, hints in profile.column_hints.items():
        match = _resolve_column(df, hints)
        if match:
            if match not in resolved:
                resolved.append(match)
        elif profile.id != "generic":
            missing.append(role)

    return resolved, missing


def _empty_mask(series: pd.Series) -> pd.Series:
    stripped = series.astype(str).str.strip()
    return series.isna() | (stripped == "") | (stripped.str.lower() == "nan")


def empty_cells_per_row(df: pd.DataFrame) -> pd.Series:
    """Count null/empty cells per row (matches contract not_null rules)."""
    if df.empty or len(df.columns) == 0:
        return pd.Series(dtype=int)
    empty = df.apply(lambda col: _empty_mask(col))
    return empty.sum(axis=1)


def _compute_dimensions(
    df: pd.DataFrame,
    profiles: List[ColumnProfile],
    profile: ProfileDefinition,
    required_columns: List[str],
) -> Dict[str, float]:
    n_cols = max(len(profiles), 1)
    dup_count = int(df.duplicated().sum())
    dup_pct = (dup_count / len(df)) * 100 if len(df) > 0 else 0

    focus = [p for p in profiles if p.name in required_columns] if required_columns else profiles
    if not focus:
        focus = profiles

    avg_null = sum(p.null_pct for p in focus) / max(len(focus), 1)
    completeness = max(0.0, 100.0 - avg_null)

    numeric = [p for p in profiles if p.dtype == "numeric"]
    avg_outlier = (
        sum(p.outlier_pct for p in numeric) / len(numeric) if numeric else 0.0
    )
    outliers = max(0.0, 100.0 - avg_outlier)

    mixed_cols = sum(1 for p in profiles if p.mixed_type_pct > 5)
    type_consistency = max(0.0, 100.0 - (mixed_cols / n_cols) * 100)

    low_card = sum(
        1
        for p in profiles
        if p.dtype == "numeric" and p.cardinality < 0.05 and p.unique_count < 20
    )
    cardinality = max(0.0, 100.0 - (low_card / n_cols) * 100)

    deep_cols = sum(
        1
        for p in profiles
        if p.date_format_count >= 2
        or p.invalid_email_count > 0
        or p.encoding_issues > 0
    )
    deep_checks = max(0.0, 100.0 - (deep_cols / n_cols) * 100)

    uniqueness = max(0.0, 100.0 - min(dup_pct * 2, 100))

    validity = 100.0
    if required_columns:
        viol = 0
        total = len(df) * len(required_columns)
        for col in required_columns:
            if col in df.columns:
                viol += int(_empty_mask(df[col]).sum())
        validity = max(0.0, 100.0 - (viol / total * 100) if total else 100.0)

    timeliness = 100.0
    date_col = _resolve_column(
        df,
        profile.column_hints.get("date", [])
        + profile.column_hints.get("event_date", []),
    )
    if date_col and len(df) > 0:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        valid = parsed.dropna()
        if len(valid) > 0:
            max_date = valid.max()
            if getattr(max_date, "tzinfo", None) is not None:
                max_date = max_date.tz_localize(None)
            days_old = (pd.Timestamp.now() - max_date).days
            timeliness = max(0.0, 100.0 - min(days_old / 3.65, 100))

    precision = 100.0
    if numeric:
        extreme = sum(p.extreme_outlier_count for p in numeric)
        precision = max(0.0, 100.0 - min(extreme / max(len(df), 1) * 500, 100))

    compliance = validity
    if email_col := _resolve_column(df, profile.column_hints.get("email", [])):
        invalid = next(
            (p.invalid_email_count for p in profiles if p.name == email_col),
            0,
        )
        non_null = int(df[email_col].notna().sum())
        if non_null > 0:
            compliance = max(0.0, 100.0 - (invalid / non_null * 100))

    label_quality = 100.0
    label_col = _resolve_column(df, profile.column_hints.get("label", []))
    if label_col:
        null_pct = next((p.null_pct for p in profiles if p.name == label_col), 0.0)
        label_quality = max(0.0, 100.0 - null_pct)

    all_dims = {
        "completeness": completeness,
        "uniqueness": uniqueness,
        "outliers": outliers,
        "type_consistency": type_consistency,
        "cardinality": cardinality,
        "deep_checks": deep_checks,
        "validity": validity,
        "timeliness": timeliness,
        "precision": precision,
        "compliance": compliance,
        "label_quality": label_quality,
    }
    return {k: round(v, 2) for k, v in all_dims.items()}


def _weighted_score(
    profile: ProfileDefinition, dimensions: Dict[str, float]
) -> Tuple[float, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    total = 0.0
    for dim, weight in profile.weights.items():
        score = dimensions.get(dim, 100.0)
        contrib = score * weight
        total += contrib
        rows.append(
            {
                "dimension": dim,
                "score": score,
                "weight": weight,
                "weighted_contribution": round(contrib, 2),
            }
        )
    return round(total, 2), rows


@dataclass
class ContractRule:
    id: str
    name: str
    severity: str  # critical | warning
    rule_type: str
    columns: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


def build_contract_rules(
    df: pd.DataFrame,
    profile: ProfileDefinition,
    required_columns: List[str],
) -> List[ContractRule]:
    rules: List[ContractRule] = [
        ContractRule(
            id="no_duplicate_rows",
            name="No duplicate rows",
            severity="warning",
            rule_type="no_duplicate_rows",
        ),
    ]

    for col in required_columns:
        if col in df.columns:
            rules.append(
                ContractRule(
                    id=f"not_null_{col}",
                    name=f"Required: {col} not null/empty",
                    severity="critical",
                    rule_type="not_null",
                    columns=[col],
                )
            )

    if profile.id == "retail":
        store = _resolve_column(df, profile.column_hints["store_id"])
        dt = _resolve_column(df, profile.column_hints["date"])
        sku = _resolve_column(df, profile.column_hints["sku"])
        sales = _resolve_column(df, profile.column_hints["sales"])
        if store and dt and sku:
            rules.append(
                ContractRule(
                    id="unique_transaction",
                    name=f"Unique ({store}, {dt}, {sku})",
                    severity="critical",
                    rule_type="unique",
                    columns=[store, dt, sku],
                )
            )
        if sales:
            rules.append(
                ContractRule(
                    id="sales_non_negative",
                    name=f"{sales} ≥ 0",
                    severity="critical",
                    rule_type="min_value",
                    columns=[sales],
                    params={"min": 0},
                )
            )

    if profile.id == "financial" and (
        email := _resolve_column(df, profile.column_hints.get("email", []))
    ):
        rules.append(
            ContractRule(
                id="email_format",
                name=f"Valid email format ({email})",
                severity="warning",
                rule_type="regex",
                columns=[email],
                params={"pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
            )
        )

    if profile.id == "ml_training" and (
        label := _resolve_column(df, profile.column_hints.get("label", []))
    ):
        rules.append(
            ContractRule(
                id="label_present",
                name=f"Label column present ({label})",
                severity="critical",
                rule_type="not_null",
                columns=[label],
            )
        )

    if profile.id == "survey":
        if respondent := _resolve_column(
            df, profile.column_hints.get("respondent_id", [])
        ):
            rules.append(
                ContractRule(
                    id="unique_respondent",
                    name=f"Unique respondent ({respondent})",
                    severity="warning",
                    rule_type="unique",
                    columns=[respondent],
                )
            )
        threshold = 2
        rules.append(
            ContractRule(
                id="high_item_missingness",
                name=f"Rows with more than {threshold} empty items",
                severity="warning",
                rule_type="max_empty_cells_per_row",
                params={"max_empty": threshold},
            )
        )

    return rules


def _sample_failures(
    df: pd.DataFrame, mask: pd.Series, limit: int = 5
) -> List[Dict[str, Any]]:
    if mask.sum() == 0:
        return []
    sample = df.loc[mask].head(limit)
    return [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in sample.to_dict(orient="records")
    ]


def evaluate_rule(df: pd.DataFrame, rule: ContractRule) -> Dict[str, Any]:
    n = len(df)
    if n == 0:
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": True,
            "violation_count": 0,
            "violation_pct": 0.0,
            "total_checked": 0,
            "message": "Empty dataset",
            "sample_failures": [],
        }

    if rule.rule_type == "no_duplicate_rows":
        dup = int(df.duplicated().sum())
        passed = dup == 0
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": passed,
            "violation_count": dup,
            "violation_pct": round(dup / n * 100, 2),
            "total_checked": n,
            "message": f"{dup} duplicate row(s)" if dup else "All rows unique",
            "sample_failures": _sample_failures(df, df.duplicated(keep=False)),
        }

    if rule.rule_type == "not_null":
        col = rule.columns[0]
        mask = _empty_mask(df[col])
        viol = int(mask.sum())
        passed = viol == 0
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": passed,
            "violation_count": viol,
            "violation_pct": round(viol / n * 100, 2),
            "total_checked": n,
            "message": f"{viol} null/empty value(s) in {col}" if viol else f"{col} complete",
            "sample_failures": _sample_failures(df, mask),
        }

    if rule.rule_type == "unique":
        dup_mask = df.duplicated(subset=rule.columns, keep=False)
        viol = int(dup_mask.sum())
        passed = viol == 0
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": passed,
            "violation_count": viol,
            "violation_pct": round(viol / n * 100, 2),
            "total_checked": n,
            "message": f"{viol} row(s) violate uniqueness" if viol else "Composite key unique",
            "sample_failures": _sample_failures(df, dup_mask),
        }

    if rule.rule_type == "min_value":
        col = rule.columns[0]
        nums = pd.to_numeric(df[col], errors="coerce")
        min_v = rule.params.get("min", 0)
        mask = nums.notna() & (nums < min_v)
        viol = int(mask.sum())
        checked = int(nums.notna().sum())
        passed = viol == 0
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": passed,
            "violation_count": viol,
            "violation_pct": round(viol / max(checked, 1) * 100, 2),
            "total_checked": checked,
            "message": f"{viol} value(s) below {min_v}" if viol else f"All {col} ≥ {min_v}",
            "sample_failures": _sample_failures(df, mask),
        }

    if rule.rule_type == "regex":
        col = rule.columns[0]
        pattern = re.compile(rule.params["pattern"])
        non_empty = df[col].dropna().astype(str).str.strip()
        non_empty = non_empty[non_empty != ""]
        if len(non_empty) == 0:
            passed = True
            viol = 0
            mask = pd.Series(False, index=df.index)
        else:
            valid = non_empty.apply(lambda v: bool(pattern.match(v)))
            viol = int((~valid).sum())
            passed = viol == 0
            bad_idx = non_empty.index[~valid.values]
            mask = df.index.isin(bad_idx)
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": passed,
            "violation_count": viol,
            "violation_pct": round(viol / max(len(non_empty), 1) * 100, 2),
            "total_checked": len(non_empty),
            "message": f"{viol} invalid format(s)" if viol else "Format valid",
            "sample_failures": _sample_failures(df, pd.Series(mask, index=df.index)),
        }

    if rule.rule_type == "max_empty_cells_per_row":
        threshold = int(rule.params.get("max_empty", 3))
        counts = empty_cells_per_row(df)
        mask = counts > threshold
        viol = int(mask.sum())
        passed = viol == 0
        return {
            "rule_id": rule.id,
            "name": rule.name,
            "severity": rule.severity,
            "passed": passed,
            "violation_count": viol,
            "violation_pct": round(viol / n * 100, 2),
            "total_checked": n,
            "message": (
                f"{viol} row(s) with more than {threshold} empty items"
                if viol
                else f"No rows exceed {threshold} empty items"
            ),
            "sample_failures": _sample_failures(df, mask),
        }

    return {
        "rule_id": rule.id,
        "name": rule.name,
        "severity": rule.severity,
        "passed": True,
        "violation_count": 0,
        "violation_pct": 0.0,
        "total_checked": n,
        "message": "Unknown rule type — skipped",
        "sample_failures": [],
    }


def assess_profile(
    df: pd.DataFrame,
    profiles: List[ColumnProfile],
    profile_id: str,
    user_required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    profile = PROFILES.get(profile_id, PROFILES["generic"])
    required, missing_user = resolve_profile_columns(df, profile, user_required)
    missing_hints: List[str] = []
    if not user_required and profile.id != "generic":
        _, missing_hints = resolve_profile_columns(df, profile, None)

    dimensions = _compute_dimensions(df, profiles, profile, required)
    overall, dimension_rows = _weighted_score(profile, dimensions)
    level = _level_from_score(overall)

    rules = build_contract_rules(df, profile, required)
    rule_results = [evaluate_rule(df, r) for r in rules]
    critical_fail = any(
        not r["passed"] and r["severity"] == "critical" for r in rule_results
    )

    return {
        "profile_id": profile.id,
        "profile_label": profile.label,
        "source": profile.source,
        "required_columns": required,
        "missing_required_columns": missing_user,
        "missing_column_hints": missing_hints,
        "dimension_scores": dimension_rows,
        "overall": overall,
        "level": level.value,
        "contract_passed": not critical_fail,
        "rules_passed": sum(1 for r in rule_results if r["passed"]),
        "rules_total": len(rule_results),
        "rules": rule_results,
    }
