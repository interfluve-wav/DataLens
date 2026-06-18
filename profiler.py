"""
Core data profiling engine for DataLens.
Handles CSV analysis, quality scoring, and recommendations.
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import iqr
import chardet
from typing import Dict, List, Tuple, Optional, Any
import json
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
    cardinality: float  # unique / total

    # Numeric stats
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    outlier_count: int = 0
    outlier_pct: float = 0.0

    # Categorical stats
    top_values: Optional[List[Tuple[Any, int]]] = None

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
    breakdown: Dict[str, float]  # issue_type -> penalty
    column_scores: Dict[str, float]


@dataclass
class SchemaDrift:
    added_columns: List[str]
    removed_columns: List[str]
    type_changed: List[Tuple[str, str, str]]  # (col, old_type, new_type)
    distribution_shifted: List[Tuple[str, float]]  # (col, p_value)
    summary: str


def detect_encoding(file_bytes: bytes) -> str:
    """Detect file encoding using chardet."""
    result = chardet.detect(file_bytes)
    return result.get('encoding', 'utf-8')


def detect_delimiter(file_bytes: str, sample_size: int = 1024) -> str:
    """Auto-detect CSV delimiter."""
    sample = file_bytes[:sample_size]
    delimiters = [',', '\t', ';', '|']
    counts = {d: sample.count(d) for d in delimiters}
    return max(counts, key=counts.get)


def load_csv(file_bytes: bytes) -> pd.DataFrame:
    """Load CSV with auto-detected encoding and delimiter."""
    encoding = detect_encoding(file_bytes)
    
    # Try to decode
    try:
        text = file_bytes.decode(encoding)
    except UnicodeDecodeError:
        text = file_bytes.decode('utf-8', errors='replace')
    
    delimiter = detect_delimiter(text)
    
    return pd.read_csv(pd.io.common.BytesIO(file_bytes), encoding=encoding, delimiter=delimiter)


def profile_column(series: pd.Series, name: str) -> ColumnProfile:
    """Profile a single column."""
    total = len(series)
    null_count = series.isna().sum()
    null_pct = (null_count / total * 100) if total > 0 else 0
    unique_count = series.nunique()
    cardinality = unique_count / total if total > 0 else 0
    
    # Determine dtype
    dtype = str(series.dtype)
    if pd.api.types.is_bool_dtype(series):
        dtype = 'boolean'
    elif pd.api.types.is_numeric_dtype(series):
        dtype = 'numeric'
    elif pd.api.types.is_datetime64_any_dtype(series):
        dtype = 'datetime'
    else:
        dtype = 'categorical'
    
    profile = ColumnProfile(
        name=name,
        dtype=dtype,
        null_pct=null_pct,
        null_count=int(null_count),
        unique_count=int(unique_count),
        total_count=int(total),
        cardinality=cardinality
    )
    
    if dtype == 'numeric':
        clean = series.dropna()
        if len(clean) > 0:
            profile.mean = float(clean.mean())
            profile.median = float(clean.median())
            profile.std = float(clean.std())
            profile.min_val = float(clean.min())
            profile.max_val = float(clean.max())
            
            # IQR outlier detection
            if len(clean) >= 4:
                q1 = clean.quantile(0.25)
                q3 = clean.quantile(0.75)
                iqr_val = q3 - q1
                lower = q1 - 1.5 * iqr_val
                upper = q3 + 1.5 * iqr_val
                outliers = clean[(clean < lower) | (clean > upper)]
                profile.outlier_count = len(outliers)
                profile.outlier_pct = (len(outliers) / len(clean)) * 100
    
    elif dtype in ['categorical', 'datetime', 'boolean']:
        # Top 5 values
        vc = series.value_counts().head(5)
        profile.top_values = [(str(k), int(v)) for k, v in vc.items()]
    
    return profile


def calculate_column_quality(profile: ColumnProfile) -> Tuple[float, QualityLevel, List[str], List[str]]:
    """Calculate quality score for a single column."""
    score = 100.0
    issues = []
    recommendations = []
    
    # Null penalty
    if profile.null_pct > 0:
        null_penalty = min(profile.null_pct * 1.5, 40)
        score -= null_penalty
        issues.append(f"{profile.null_pct:.1f}% null values")
        if profile.null_pct > 50:
            recommendations.append(f"Column `{profile.name}` is {profile.null_pct:.1f}% null — consider dropping")
        else:
            recommendations.append(f"Column `{profile.name}` is {profile.null_pct:.1f}% null — impute with {'median' if profile.dtype == 'numeric' else 'mode'}")
    
    # Outlier penalty (numeric only)
    if profile.dtype == 'numeric' and profile.outlier_pct > 0:
        outlier_penalty = min(profile.outlier_pct * 2, 30)
        score -= outlier_penalty
        issues.append(f"{profile.outlier_pct:.1f}% outliers (IQR method)")
        recommendations.append(f"Column `{profile.name}` has {profile.outlier_pct:.1f}% outliers — review for data entry errors")
    
    # Low cardinality flag (numeric treated as categorical)
    if profile.dtype == 'numeric' and profile.cardinality < 0.05 and profile.unique_count < 20:
        score -= 15
        issues.append("Low cardinality numeric (likely categorical)")
        recommendations.append(f"Column `{profile.name}` has only {profile.unique_count} unique values — consider treating as categorical")
    
    # Type mismatch detection (strings that could be dates/numbers)
    if profile.dtype == 'categorical' and profile.top_values:
        # Check if values look like dates
        sample_vals = [v[0] for v in profile.top_values[:3]]
        date_like = sum(1 for v in sample_vals if _looks_like_date(v)) / len(sample_vals)
        if date_like > 0.6:
            score -= 20
            issues.append("Likely date column parsed as string")
            recommendations.append(f"Column `{profile.name}` appears to contain dates — cast to DATE type")
    
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


def _looks_like_date(val: str) -> bool:
    """Quick heuristic to check if string looks like a date."""
    import re
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
        r'^\d{2}-\d{2}-\d{4}$',  # DD-MM-YYYY
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
    ]
    return any(re.match(p, str(val)) for p in date_patterns)


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
    
    # Calculate overall quality score (weighted by column importance)
    if column_profiles:
        # Weight: nulls 25%, duplicates 20%, outliers 20%, type mismatch 15%, low cardinality 10%, schema drift 10%
        # For single file, schema drift = 0
        null_penalty = np.mean([p.null_pct for p in column_profiles]) * 0.25
        outlier_penalty = np.mean([p.outlier_pct for p in column_profiles if p.dtype == 'numeric']) * 0.20 if any(p.dtype == 'numeric' for p in column_profiles) else 0
        
        # Duplicate check
        dup_count = df.duplicated().sum()
        dup_pct = (dup_count / len(df)) * 100 if len(df) > 0 else 0
        dup_penalty = min(dup_pct * 2, 20)
        
        # Type mismatch penalty
        type_mismatch_cols = sum(1 for p in column_profiles if "date column parsed as string" in " ".join(p.issues))
        type_penalty = (type_mismatch_cols / len(column_profiles)) * 15 if column_profiles else 0
        
        # Low cardinality penalty
        low_card_cols = sum(1 for p in column_profiles if "Low cardinality" in " ".join(p.issues))
        cardinality_penalty = (low_card_cols / len(column_profiles)) * 10 if column_profiles else 0
        
        total_penalty = null_penalty + outlier_penalty + dup_penalty + type_penalty + cardinality_penalty
        overall = max(0, 100 - total_penalty)
    else:
        overall = 100
        null_penalty = outlier_penalty = dup_penalty = type_penalty = cardinality_penalty = 0
    
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
            'low_cardinality': cardinality_penalty
        },
        column_scores={p.name: p.quality_score for p in column_profiles}
    )
    
    return column_profiles, quality_score


def detect_schema_drift(baseline_df: pd.DataFrame, new_df: pd.DataFrame) -> SchemaDrift:
    """Compare two dataframes for schema drift."""
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
        
        # KS test for numeric columns
        if pd.api.types.is_numeric_dtype(baseline_df[col]) and pd.api.types.is_numeric_dtype(new_df[col]):
            old_clean = baseline_df[col].dropna()
            new_clean = new_df[col].dropna()
            if len(old_clean) > 10 and len(new_clean) > 10:
                try:
                    stat, p_value = stats.ks_2samp(old_clean, new_clean)
                    if p_value < 0.05:
                        distribution_shifted.append((col, p_value))
                except:
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


def apply_fixes(df: pd.DataFrame, column_profiles: List[ColumnProfile], 
                fixes: Dict[str, str]) -> pd.DataFrame:
    """Apply selected fixes to a copy of the dataframe."""
    result = df.copy()
    
    for col, fix_type in fixes.items():
        if col not in result.columns:
            continue
            
        profile = next((p for p in column_profiles if p.name == col), None)
        if not profile:
            continue
        
        if fix_type == 'drop_nulls':
            result = result.dropna(subset=[col])
        elif fix_type == 'impute_median' and profile.dtype == 'numeric':
            result[col] = result[col].fillna(result[col].median())
        elif fix_type == 'impute_mode':
            result[col] = result[col].fillna(result[col].mode().iloc[0] if not result[col].mode().empty else '')
        elif fix_type == 'cast_date' and profile.dtype == 'categorical':
            result[col] = pd.to_datetime(result[col], errors='coerce')
        elif fix_type == 'dedupe':
            result = result.drop_duplicates()
    
    return result


def generate_markdown_report(
    column_profiles: List[ColumnProfile],
    quality_score: QualityScore,
    schema_drift: Optional[SchemaDrift] = None,
    filename: str = "data.csv"
) -> str:
    """Generate a markdown quality report."""
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
    
    lines.extend([
        "",
        "## Recommendations",
        ""
    ])
    
    all_recs = []
    for p in column_profiles:
        all_recs.extend(p.recommendations)
    
    if all_recs:
        for i, rec in enumerate(all_recs, 1):
            lines.append(f"{i}. {rec}")
    else:
        lines.append("No issues detected — data looks clean!")
    
    if schema_drift:
        lines.extend([
            "",
            "## Schema Drift Detection",
            "",
            f"**Summary:** {schema_drift.summary}",
            ""
        ])
        
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
    
    lines.extend([
        "",
        "---",
        "*Generated by DataLens — CSV Quality Analyzer*"
    ])
    
    return "\n".join(lines)