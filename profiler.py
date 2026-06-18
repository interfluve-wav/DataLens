"""
Core data profiling engine for DataLens.
Handles CSV analysis, quality scoring, and recommendations.
"""

import pandas as pd
import numpy as np
from scipy import stats
import chardet
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class QualityLevel(Enum):
    EXCELLENT = "🟢 Excellent"
    GOOD = "🟢 Good"
    NEEDS_CLEANING = "🟡 Needs Cleaning"
    POOR = "🔴 Poor"


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_pct: float
    null_count: int
    unique_count: int
    total_count: int
    cardinality: float

    # Numeric stats
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    outlier_count: int = 0
    outlier_pct: float = 0.0
    negative_count: int = 0
    negative_pct: float = 0.0

    # Categorical stats
    top_values: Optional[List[Tuple[Any, int]]] = None
    whitespace_count: int = 0
    whitespace_pct: float = 0.0
    encoding_issues: int = 0

    # Deep analysis
    mixed_type_pct: float = 0.0
    invalid_email_count: int = 0
    invalid_email_pct: float = 0.0
    date_format_count: int = 0
    extreme_outlier_count: int = 0

    # Quality
    quality_score: float = 100.0
    quality_level: QualityLevel = QualityLevel.EXCELLENT
    issues: List[str] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class QualityScore:
    overall: float
    level: QualityLevel
    breakdown: Dict[str, float]
    column_scores: Dict[str, float]


@dataclass
class SchemaDrift:
    added_columns: List[str]
    removed_columns: List[str]
    type_changed: List[Tuple[str, str, str]]
    distribution_shifted: List[Tuple[str, float]]
    summary: str


_DATE_PATTERNS = [
    (re.compile(r'^\d{4}-\d{2}-\d{2}$'), 'ISO'),
    (re.compile(r'^\d{2}/\d{2}/\d{4}$'), 'US'),
    (re.compile(r'^\d{2}-\d{2}-\d{4}$'), 'EU'),
    (re.compile(r'^\d{4}/\d{2}/\d{2}$'), 'ISO_SLASH'),
    (re.compile(r'^\d{4}-\d{2}$'), 'YYYY-MM'),
    (re.compile(r'^\d{4}$'), 'YYYY'),
    (re.compile(r'^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$'), 'TEXT'),
]


def _classify_date_format(val: str) -> Optional[str]:
    for pattern, fmt in _DATE_PATTERNS:
        if pattern.match(val.strip()):
            return fmt
    return None


def _looks_like_email(val: str) -> Tuple[bool, str]:
    val = val.strip()
    if '@' not in val:
        return False, "missing @"
    parts = val.split('@')
    if len(parts) != 2:
        return False, "multiple @ symbols"
    local, domain = parts
    if not local:
        return False, "empty local part"
    if '.' not in domain:
        return False, "domain has no dot"
    if '..' in domain or domain.startswith('.') or domain.endswith('.'):
        return False, "invalid domain"
    return True, ""


def _has_encoding_issues(val: str) -> bool:
    """Detect mojibake / encoding corruption."""
    mojibake = [
        'Ã©', 'Ã¼', 'Ã¤', 'Ã¶', 'Ã±',  # common latin corruptions
        'â€™', 'â€"', 'â€œ', 'â€', 'Â£',
        'Å¡', 'Å¾', 'Å', 'Ä', 'Å',
    ]
    for pattern in mojibake:
        if pattern in val:
            return True
    return False


def _is_numeric_string(val: str) -> bool:
    """Check if a string looks numeric (int/float/negative/decimal)."""
    val = val.strip()
    try:
        float(val)
        return True
    except ValueError:
        return False


def _has_whitespace_issues(val: str) -> bool:
    return val != val.strip()


def detect_encoding(file_bytes: bytes) -> str:
    result = chardet.detect(file_bytes)
    return result.get('encoding', 'utf-8')


def detect_delimiter(file_bytes_str: str, sample_size: int = 2048) -> str:
    sample = file_bytes_str[:sample_size]
    delimiters = [',', '\t', ';', '|']
    counts = {d: sample.count(d) for d in delimiters}
    return max(counts, key=counts.get)


def load_csv(file_bytes: bytes) -> pd.DataFrame:
    encoding = detect_encoding(file_bytes)
    try:
        text = file_bytes.decode(encoding)
    except UnicodeDecodeError:
        text = file_bytes.decode('utf-8', errors='replace')
    delimiter = detect_delimiter(text)

    df = pd.read_csv(
        pd.io.common.BytesIO(file_bytes),
        encoding=encoding,
        delimiter=delimiter,
        keep_default_na=True,
        na_values=['', 'NA', 'N/A', 'NULL', 'null', 'NaN', 'nan'],
        dtype=str,  # read all as strings to preserve mixed types
    )
    return df


def _try_convert_numeric(series: pd.Series) -> Optional[pd.Series]:
    """Try to convert string series to numeric, return None if too mixed."""
    cleaned = series.str.strip()
    cleaned = cleaned.replace(['', 'NA', 'N/A', 'NULL', 'null', 'NaN', 'nan', 'TBD', 'N/A', 'n/a'], np.nan)
    converted = pd.to_numeric(cleaned, errors='coerce')
    null_ratio = converted.isna().sum() / len(series)
    # If >40% are non-numeric, don't treat as numeric column
    original_nulls = series.isna().sum()
    introduced_nulls = converted.isna().sum() - original_nulls
    if introduced_nulls > 0 and (introduced_nulls / len(series)) > 0.3:
        return None
    return converted


def profile_column(series_raw: pd.Series, name: str) -> ColumnProfile:
    """Profile a single column with deep analysis."""
    total = len(series_raw)
    null_count = int(series_raw.isna().sum())
    null_pct = (null_count / total * 100) if total > 0 else 0
    unique_count = int(series_raw.nunique())
    cardinality = unique_count / total if total > 0 else 0

    # Non-null values for analysis
    non_null = series_raw.dropna()

    # ID column detection: high cardinality + mixed alphanumeric values
    is_id_column = False
    if cardinality > 0.65 and unique_count > 50:
        sample = series_raw.dropna().astype(str).head(50)
        alphanumeric_count = sum(1 for v in sample if re.search(r'[A-Za-z].*\d|\d.*[A-Za-z]', v.strip()))
        pure_numeric_count = sum(1 for v in sample if v.strip().isdigit())
        total_in_sample = max(len(sample), 1)
        # If most sample values are alphanumeric codes, it's an ID column
        if alphanumeric_count / total_in_sample > 0.2 or cardinality > 0.7:
            is_id_column = True

    # Try to determine if this is actually numeric (despite string parsing)
    numeric_attempt = _try_convert_numeric(series_raw)
    # ID column detection: skip numeric analysis
    if is_id_column:
        dtype = 'categorical'
    elif numeric_attempt is not None:
        # Check for string values that didn't parse (mixed types)
        mixed_mask = numeric_attempt.isna() & ~series_raw.isna()
        mixed_count = int(mixed_mask.sum())
        mixed_pct = (mixed_count / total * 100) if total > 0 else 0

        # If mostly parseable as numeric, treat as numeric
        non_numeric_ratio = numeric_attempt.isna().sum() / total if total > 0 else 0
        if non_numeric_ratio < 0.3:
            dtype = 'numeric'
            clean = numeric_attempt.dropna()
            profile = ColumnProfile(
                name=name, dtype=dtype,
                null_pct=null_pct, null_count=null_count,
                unique_count=unique_count, total_count=total,
                cardinality=cardinality,
                mixed_type_pct=mixed_pct,
            )
            if len(clean) > 0:
                profile.mean = float(clean.mean())
                profile.median = float(clean.median())
                profile.std = float(clean.std()) if len(clean) > 1 else 0.0
                profile.min_val = float(clean.min())
                profile.max_val = float(clean.max())
                q1 = float(clean.quantile(0.25))
                q3 = float(clean.quantile(0.75))
                iqr_val = q3 - q1
                lower = q1 - 1.5 * iqr_val
                upper = q3 + 1.5 * iqr_val
                outliers = clean[(clean < lower) | (clean > upper)]
                profile.outlier_count = len(outliers)
                profile.outlier_pct = (len(outliers) / len(clean)) * 100 if len(clean) > 0 else 0

                # Negative value detection
                negatives = clean[clean < 0]
                profile.negative_count = len(negatives)
                profile.negative_pct = (len(negatives) / len(clean)) * 100 if len(clean) > 0 else 0

                # Extreme outlier detection (3-sigma or beyond 5× IQR)
                extreme_lower = q1 - 5.0 * iqr_val
                extreme_upper = q3 + 5.0 * iqr_val
                extreme = clean[(clean < extreme_lower) | (clean > extreme_upper)]
                profile.extreme_outlier_count = len(extreme)
            return profile

    # Categorical / text column — deep analysis
    dtype = 'categorical'
    profile = ColumnProfile(
        name=name, dtype=dtype,
        null_pct=null_pct, null_count=null_count,
        unique_count=unique_count, total_count=total,
        cardinality=cardinality,
    )

    # Top values
    vc = series_raw.value_counts().head(5)
    profile.top_values = [(str(k), int(v)) for k, v in vc.items()]

    # Date format detection
    if len(non_null) > 0:
        date_formats = set()
        for val in non_null.astype(str).dropna().head(100):
            fmt = _classify_date_format(val)
            if fmt:
                date_formats.add(fmt)
        profile.date_format_count = len(date_formats)

    # Whitespace issues
    str_vals = non_null.astype(str)
    whitespace = str_vals[str_vals.apply(_has_whitespace_issues)]
    profile.whitespace_count = len(whitespace)
    profile.whitespace_pct = (len(whitespace) / len(non_null)) * 100 if len(non_null) > 0 else 0

    # Encoding issues
    bad_encoding = str_vals[str_vals.apply(_has_encoding_issues)]
    profile.encoding_issues = len(bad_encoding)

    # Email validation (if column name suggests email or values look like email)
    if 'email' in name.lower() or any('@' in str(v) for v in non_null.head(10)):
        invalid = 0
        for val in str_vals:
            is_valid, _ = _looks_like_email(val)
            if not is_valid:
                invalid += 1
        profile.invalid_email_count = invalid
        profile.invalid_email_pct = (invalid / len(non_null)) * 100 if len(non_null) > 0 else 0

    # Mixed type detection: values that look numeric but column is all-categorical
    str_clean = non_null.dropna().astype(str).str.strip()
    numeric_looking = str_clean[str_clean.apply(_is_numeric_string)]
    if len(numeric_looking) > 0 and len(numeric_looking) < len(str_clean) and len(str_clean) > 0:
        profile.mixed_type_pct = (1 - len(numeric_looking) / len(str_clean)) * 100

    return profile


def calculate_column_quality(profile: ColumnProfile) -> Tuple[float, QualityLevel, List[str], List[str]]:
    """Calculate quality score for a single column with deep diagnostics."""
    score = 100.0
    issues = []
    recommendations = []

    # Null penalty
    if profile.null_pct > 0:
        null_penalty = min(profile.null_pct * 1.2, 30)
        score -= null_penalty
        issues.append(f"{profile.null_pct:.1f}% null values")
        if profile.null_pct > 60:
            recommendations.append(f"Column `{profile.name}` is {profile.null_pct:.1f}% null — consider dropping")
        elif profile.null_pct > 0:
            rec_type = 'median' if profile.dtype == 'numeric' else 'mode'
            recommendations.append(f"Column `{profile.name}` is {profile.null_pct:.1f}% null — impute with {rec_type}")

    # Mixed type detection (numeric flag)
    if profile.mixed_type_pct > 5:
        mixed_penalty = min(profile.mixed_type_pct * 0.8, 20)
        score -= mixed_penalty
        issues.append(f"{profile.mixed_type_pct:.1f}% non-numeric values in otherwise numeric column")
        recommendations.append(f"Column `{profile.name}` has mixed types — investigate non-numeric entries like 'TBD', 'N/A'")

    # Outlier penalty (numeric)
    if profile.dtype == 'numeric' and profile.outlier_pct > 0:
        outlier_penalty = min(profile.outlier_pct * 1.0, 25)
        score -= outlier_penalty
        issues.append(f"{profile.outlier_pct:.1f}% outliers (IQR method)")
        recommendations.append(f"Column `{profile.name}` has {profile.outlier_pct:.1f}% outliers — review for data entry errors")

    # Extreme outlier penalty
    if profile.extreme_outlier_count > 0:
        extreme_penalty = min(profile.extreme_outlier_count * 3, 20)
        score -= extreme_penalty
        issues.append(f"{profile.extreme_outlier_count} extreme outlier(s) (5× IQR)")
        recommendations.append(f"Column `{profile.name}` has {profile.extreme_outlier_count} extreme outlier(s) — likely data entry errors")

    # Negative value detection (skip geo-coordinates and temperatures)
    if profile.negative_count > 0 and not any(kw in profile.name.lower() for kw in ['lat', 'lon', 'coord', 'temp']):
        neg_penalty = min(profile.negative_pct * 1.5, 15)
        score -= neg_penalty
        issues.append(f"{profile.negative_count} negative value(s) ({profile.negative_pct:.1f}%)")
        recommendations.append(f"Column `{profile.name}` has negative values — validate with source system")

    # Low cardinality numeric
    if profile.dtype == 'numeric' and profile.cardinality < 0.05 and profile.unique_count < 20:
        score -= 10
        issues.append("Low cardinality numeric (likely categorical)")
        recommendations.append(f"Column `{profile.name}` has only {profile.unique_count} unique values — consider treating as categorical")

    # Date format inconsistency
    if profile.date_format_count >= 2:
        score -= 15
        issues.append(f"{profile.date_format_count} different date formats detected")
        recommendations.append(f"Column `{profile.name}` has mixed date formats — standardize to ISO 8601")

    # Date column parsed as string
    if profile.date_format_count >= 1 and profile.dtype == 'categorical' and profile.mixed_type_pct < 50:
        score -= 10
        if "date" not in " ".join(issues).lower():
            issues.append("Likely date column parsed as string")
        recommendations.append(f"Column `{profile.name}` appears to contain dates — cast to DATE type")

    # Invalid email detection
    if profile.invalid_email_count > 0:
        email_penalty = min(profile.invalid_email_pct * 0.8, 15)
        score -= email_penalty
        issues.append(f"{profile.invalid_email_count} invalid email(s)")
        recommendations.append(f"Column `{profile.name}` has {profile.invalid_email_count} malformed emails — validate input")

    # Whitespace issues
    if profile.whitespace_count > 0:
        ws_penalty = min(profile.whitespace_pct * 0.5, 10)
        score -= ws_penalty
        issues.append(f"{profile.whitespace_count} value(s) with leading/trailing whitespace")
        recommendations.append(f"Column `{profile.name}` has whitespace issues — use .str.strip()")

    # Encoding issues
    if profile.encoding_issues > 0:
        score -= 10
        issues.append(f"{profile.encoding_issues} value(s) with encoding corruption (mojibake)")
        recommendations.append(f"Column `{profile.name}` has encoding issues — re-import in UTF-8")

    score = max(0, min(100, score))
    if score >= 90:
        level = QualityLevel.EXCELLENT
    elif score >= 70:
        level = QualityLevel.GOOD
    elif score >= 50:
        level = QualityLevel.NEEDS_CLEANING
    else:
        level = QualityLevel.POOR
    return score, level, issues, recommendations


def profile_dataframe(df: pd.DataFrame) -> Tuple[List[ColumnProfile], QualityScore]:
    """Profile entire dataframe and compute quality score."""
    column_profiles = []
    for col in df.columns:
        profile = profile_column(df[col], col)
        score, level, issues, recommendations = calculate_column_quality(profile)
        profile.quality_score = score
        profile.quality_level = level
        profile.issues = issues
        profile.recommendations = recommendations
        column_profiles.append(profile)

    # Overall weighted score
    if column_profiles:
        dup_count = int(df.duplicated().sum())
        dup_pct = (dup_count / len(df)) * 100 if len(df) > 0 else 0

        null_penalty = np.mean([p.null_pct for p in column_profiles]) * 0.25
        dup_penalty = min(dup_pct * 2, 20)
        outlier_penalty = np.mean([p.outlier_pct for p in column_profiles if p.dtype == 'numeric']) * 0.20 if any(p.dtype == 'numeric' for p in column_profiles) else 0
        type_mismatch_cols = sum(1 for p in column_profiles if p.mixed_type_pct > 5)
        type_penalty = (type_mismatch_cols / len(column_profiles)) * 15 if column_profiles else 0
        low_card_cols = sum(1 for p in column_profiles if p.dtype == 'numeric' and p.cardinality < 0.05 and p.unique_count < 20)
        cardinality_penalty = (low_card_cols / len(column_profiles)) * 10 if column_profiles else 0
        # Additional penalties for deep issues
        date_issue_cols = sum(1 for p in column_profiles if p.date_format_count >= 2)
        email_issue_cols = sum(1 for p in column_profiles if p.invalid_email_count > 0)
        encoding_issue_cols = sum(1 for p in column_profiles if p.encoding_issues > 0)
        deep_penalty = (date_issue_cols + email_issue_cols + encoding_issue_cols) / len(column_profiles) * 10

        total_penalty = null_penalty + outlier_penalty + dup_penalty + type_penalty + cardinality_penalty + deep_penalty
        overall = max(0, 100 - total_penalty)
    else:
        overall = 100
        dup_penalty = null_penalty = outlier_penalty = type_penalty = cardinality_penalty = deep_penalty = 0

    if overall >= 90:
        level = QualityLevel.EXCELLENT
    elif overall >= 70:
        level = QualityLevel.GOOD
    elif overall >= 50:
        level = QualityLevel.NEEDS_CLEANING
    else:
        level = QualityLevel.POOR

    quality_score = QualityScore(
        overall=overall,
        level=level,
        breakdown={
            'nulls': null_penalty,
            'duplicates': dup_penalty,
            'outliers': outlier_penalty,
            'type_mismatch': type_penalty,
            'low_cardinality': cardinality_penalty,
            'deep_issues': deep_penalty,
        },
        column_scores={p.name: p.quality_score for p in column_profiles}
    )
    return column_profiles, quality_score


def detect_schema_drift(baseline_df: pd.DataFrame, new_df: pd.DataFrame) -> SchemaDrift:
    baseline_cols = set(baseline_df.columns)
    new_cols = set(new_df.columns)
    added = list(new_cols - baseline_cols)
    removed = list(baseline_cols - new_cols)
    common = baseline_cols & new_cols
    type_changed = []
    distribution_shifted = []
    for col in common:
        old_dtype = str(baseline_df[col].dtype)
        new_dtype = str(new_df[col].dtype)
        if old_dtype != new_dtype:
            type_changed.append((col, old_dtype, new_dtype))
        if pd.api.types.is_numeric_dtype(baseline_df[col]) and pd.api.types.is_numeric_dtype(new_df[col]):
            old_clean = baseline_df[col].dropna()
            new_clean = new_df[col].dropna()
            if len(old_clean) > 10 and len(new_clean) > 10:
                try:
                    stat, p_value = stats.ks_2samp(old_clean, new_clean)
                    if p_value < 0.05:
                        distribution_shifted.append((col, p_value))
                except Exception:
                    pass
    breaking = len(type_changed) + len(removed)
    warnings = len(added) + len(distribution_shifted)
    summary = f"{breaking} breaking changes, {warnings} warnings"
    return SchemaDrift(
        added_columns=added,
        removed_columns=removed,
        type_changed=type_changed,
        distribution_shifted=distribution_shifted,
        summary=summary
    )


def apply_fixes(df: pd.DataFrame, column_profiles: List[ColumnProfile], fixes: Dict[str, str]) -> pd.DataFrame:
    result = df.copy()
    for col, fix_type in fixes.items():
        if col not in result.columns:
            continue
        if fix_type == 'drop_nulls':
            result = result.dropna(subset=[col])
        elif fix_type == 'impute_median':
            numeric_col = pd.to_numeric(result[col], errors='coerce')
            median_val = numeric_col.median()
            result[col] = result[col].fillna(str(median_val) if not pd.isna(median_val) else '')
        elif fix_type == 'impute_mode':
            mode_val = result[col].mode()
            result[col] = result[col].fillna(mode_val.iloc[0] if not mode_val.empty else '')
        elif fix_type == 'strip_whitespace':
            result[col] = result[col].astype(str).str.strip()
        elif fix_type == 'dedupe':
            result = result.drop_duplicates()
    return result


def generate_markdown_report(
    column_profiles: List[ColumnProfile],
    quality_score: QualityScore,
    schema_drift: Optional[SchemaDrift] = None,
    filename: str = "data.csv"
) -> str:
    lines = [
        f"# DataLens Quality Report: {filename}",
        "",
        f"**Overall Score:** {quality_score.overall:.1f}/100 — {quality_score.level.value}",
        "",
        "## Score Breakdown",
        ""
    ]
    for issue, penalty in quality_score.breakdown.items():
        lines.append(f"- **{issue.replace('_', ' ').title()}:** -{penalty:.1f} points")
    lines.extend([
        "",
        "## Column Overview",
        "",
        "| Column | Type | Null% | Unique | Quality | Issues |",
        "|--------|------|-------|--------|---------|--------|"
    ])
    for p in column_profiles:
        issues_str = "; ".join(p.issues) if p.issues else "—"
        lines.append(f"| {p.name} | {p.dtype} | {p.null_pct:.1f}% | {p.unique_count:,} | {p.quality_level.value} | {issues_str} |")
    lines.extend(["\n## Recommendations\n"])
    all_recs = []
    for p in column_profiles:
        all_recs.extend(p.recommendations)
    if all_recs:
        for i, rec in enumerate(all_recs, 1):
            lines.append(f"{i}. {rec}")
    else:
        lines.append("No issues detected — data looks clean!")
    if schema_drift:
        lines.extend(["\n## Schema Drift Detection\n", f"**Summary:** {schema_drift.summary}\n"])
        if schema_drift.added_columns:
            lines.append(f"**Added columns:** {', '.join(schema_drift.added_columns)}")
        if schema_drift.removed_columns:
            lines.append(f"**Removed columns:** {', '.join(schema_drift.removed_columns)}")
        if schema_drift.type_changed:
            lines.append("**Type changes:**")
            for col, old, new in schema_drift.type_changed:
                lines.append(f"  - `{col}`: {old} → {new}")
        if schema_drift.distribution_shifted:
            lines.append("**Distribution shifts (p < 0.05):**")
            for col, p_val in schema_drift.distribution_shifted:
                lines.append(f"  - `{col}`: p = {p_val:.4f}")
    lines.extend(["\n---", "*Generated by DataLens — CSV Quality Analyzer*"])
    return "\n".join(lines)