"""
DataLens — CSV Quality Analyzer
Streamlit web application
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from profiler import (
    load_csv, profile_dataframe, detect_schema_drift,
    apply_fixes, generate_markdown_report,
    ColumnProfile, QualityScore, SchemaDrift, QualityLevel
)

# Page config
st.set_page_config(
    page_title="DataLens — CSV Quality Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #00D4AA;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888;
        margin-bottom: 2rem;
    }
    .gauge-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1rem;
    }
    .metric-card {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .quality-excellent { color: #00D4AA; font-weight: bold; }
    .quality-good { color: #00D4AA; }
    .quality-needs { color: #FFAA00; font-weight: bold; }
    .quality-poor { color: #FF4444; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background: #1e1e1e;
        border-radius: 8px;
        border: 1px solid #333;
    }
    .stTabs [aria-selected="true"] {
        background: #00D4AA !important;
        color: #000 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'profiles' not in st.session_state:
    st.session_state.profiles = None
if 'quality_score' not in st.session_state:
    st.session_state.quality_score = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'baseline_df' not in st.session_state:
    st.session_state.baseline_df = None
if 'schema_drift' not in st.session_state:
    st.session_state.schema_drift = None
if 'applied_fixes' not in st.session_state:
    st.session_state.applied_fixes = {}

def create_gauge(score: float, level: QualityLevel):
    """Create a Plotly gauge chart for the quality score."""
    # Determine color based on score
    if score >= 90:
        color = "#00D4AA"
    elif score >= 70:
        color = "#00D4AA"
    elif score >= 50:
        color = "#FFAA00"
    else:
        color = "#FF4444"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Data Quality Score", 'font': {'size': 24, 'color': 'white'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#555"},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "#1e1e1e",
            'borderwidth': 2,
            'bordercolor': "#333",
            'steps': [
                {'range': [0, 50], 'color': '#331111'},
                {'range': [50, 70], 'color': '#332211'},
                {'range': [70, 90], 'color': '#113311'},
                {'range': [90, 100], 'color': '#003322'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        },
        number={'font': {'size': 48, 'color': color}}
    ))
    
    fig.update_layout(
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font={'color': 'white', 'family': 'monospace'},
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig


def create_breakdown_chart(breakdown: dict):
    """Create horizontal bar chart for score breakdown."""
    issues = list(breakdown.keys())
    penalties = list(breakdown.values())
    
    # Filter out zero penalties
    filtered = [(i, p) for i, p in zip(issues, penalties) if p > 0.1]
    if not filtered:
        return None
    
    issues, penalties = zip(*filtered)
    issues = [i.replace('_', ' ').title() for i in issues]
    
    fig = go.Figure(go.Bar(
        x=penalties,
        y=issues,
        orientation='h',
        marker_color='#FF4444',
        text=[f"-{p:.1f}" for p in penalties],
        textposition='outside',
        textfont=dict(color='white', size=12)
    ))
    
    fig.update_layout(
        title="Score Penalty Breakdown",
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font={'color': 'white'},
        xaxis_title="Penalty Points",
        yaxis_title="",
        height=max(200, len(issues) * 50),
        margin=dict(l=120, r=20, t=50, b=40),
        xaxis=dict(range=[0, max(penalties) * 1.3], gridcolor='#333'),
        yaxis=dict(gridcolor='#333')
    )
    return fig


def create_column_heatmap(profiles: list):
    """Create column quality heatmap table."""
    if not profiles:
        return None
    
    df_data = []
    for p in profiles:
        df_data.append({
            'Column': p.name,
            'Type': p.dtype,
            'Null %': f"{p.null_pct:.1f}%",
            'Unique': f"{p.unique_count:,}",
            'Quality': p.quality_score,
            'Level': p.quality_level.value
        })
    
    df = pd.DataFrame(df_data)
    
    # Color function
    def color_quality(val):
        if val >= 90:
            return 'background-color: #003322; color: #00D4AA'
        elif val >= 70:
            return 'background-color: #113311; color: #00D4AA'
        elif val >= 50:
            return 'background-color: #332211; color: #FFAA00'
        else:
            return 'background-color: #331111; color: #FF4444'
    
    styled = df.style.applymap(color_quality, subset=['Quality'])
    return styled


def create_distribution_charts(df: pd.DataFrame, profiles: list, selected_col: str):
    """Create distribution visualizations for a column."""
    profile = next((p for p in profiles if p.name == selected_col), None)
    if not profile:
        return None, None
    
    col_data = df[selected_col].dropna()
    
    if profile.dtype == 'numeric' and len(col_data) > 0:
        # Histogram with box plot
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.05,
            shared_xaxes=True
        )
        
        # Histogram
        fig.add_trace(
            go.Histogram(x=col_data, nbinsx=30, name=selected_col,
                        marker_color='#00D4AA', opacity=0.7),
            row=1, col=1
        )
        
        # Box plot
        fig.add_trace(
            go.Box(x=col_data, name=selected_col,
                  marker_color='#FF4444', boxpoints='outliers'),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f"Distribution: {selected_col}",
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117',
            font={'color': 'white'},
            height=400,
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis=dict(gridcolor='#333'),
            yaxis=dict(gridcolor='#333')
        )
        
        return fig, None
    
    elif profile.dtype in ['categorical', 'datetime', 'boolean'] and profile.top_values:
        # Bar chart for top values
        values, counts = zip(*profile.top_values[:15])
        
        fig = go.Figure(go.Bar(
            x=list(values),
            y=list(counts),
            marker_color='#00D4AA',
            text=list(counts),
            textposition='outside'
        ))
        
        fig.update_layout(
            title=f"Top Values: {selected_col}",
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117',
            font={'color': 'white'},
            height=400,
            margin=dict(l=20, r=20, t=50, b=100),
            xaxis=dict(gridcolor='#333', tickangle=-45),
            yaxis=dict(gridcolor='#333', title="Count")
        )
        
        return fig, None
    
    return None, None


def render_header():
    """Render the main header with upload buttons."""
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown('<div class="main-header">DataLens</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">CSV Quality Analyzer — Score, diagnose, and fix your data</div>', unsafe_allow_html=True)
    
    with col2:
        uploaded = st.file_uploader("Upload CSV", type=['csv'], key="main_upload")
    
    with col3:
        baseline = st.file_uploader("Upload Baseline (optional)", type=['csv'], key="baseline_upload")
    
    return uploaded, baseline


def render_quality_overview():
    """Render quality score gauge and breakdown."""
    if st.session_state.quality_score is None:
        return
    
    qs = st.session_state.quality_score
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        gauge = create_gauge(qs.overall, qs.level)
        st.plotly_chart(gauge, use_container_width=True)
        
        # Score interpretation
        level_class = {
            QualityLevel.EXCELLENT: 'quality-excellent',
            QualityLevel.GOOD: 'quality-good',
            QualityLevel.NEEDS_CLEANING: 'quality-needs',
            QualityLevel.POOR: 'quality-poor'
        }.get(qs.level, '')
        
        st.markdown(f'<div style="text-align:center; font-size:1.5rem; margin-top:1rem;">'
                    f'<span class="{level_class}">{qs.level.value}</span></div>',
                    unsafe_allow_html=True)
    
    with col2:
        breakdown_chart = create_breakdown_chart(qs.breakdown)
        if breakdown_chart:
            st.plotly_chart(breakdown_chart, use_container_width=True)
        else:
            st.info("No significant penalties — data looks clean!")
        
        # Duplicate info
        st.metric("Duplicate Rows", f"{qs.breakdown.get('duplicates', 0):.1f}% penalty")


def render_column_overview():
    """Render column overview heatmap."""
    if not st.session_state.profiles:
        return
    
    st.markdown("### Column Overview")
    
    heatmap = create_column_heatmap(st.session_state.profiles)
    if heatmap is not None:
        st.dataframe(heatmap, use_container_width=True, hide_index=True)


def render_distribution_tab():
    """Render distribution visualizations."""
    if not st.session_state.profiles or st.session_state.df is None:
        return
    
    st.markdown("### Distribution Analysis")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected = st.selectbox(
            "Select Column",
            options=[p.name for p in st.session_state.profiles],
            index=0
        )
    
    with col2:
        profile = next(p for p in st.session_state.profiles if p.name == selected)
        
        # Show column stats
        stats_cols = st.columns(4)
        with stats_cols[0]:
            st.metric("Null %", f"{profile.null_pct:.1f}%")
        with stats_cols[1]:
            st.metric("Unique", f"{profile.unique_count:,}")
        with stats_cols[2]:
            if profile.dtype == 'numeric':
                st.metric("Mean", f"{profile.mean:.2f}" if profile.mean else "—")
        with stats_cols[3]:
            if profile.dtype == 'numeric':
                st.metric("Outliers", f"{profile.outlier_pct:.1f}%")
    
    # Charts
    chart, _ = create_distribution_charts(st.session_state.df, st.session_state.profiles, selected)
    if chart:
        st.plotly_chart(chart, use_container_width=True)
    
    # Issues for this column
    if profile.issues:
        st.markdown("**Issues:**")
        for issue in profile.issues:
            st.warning(f"⚠️ {issue}")


def render_recommendations_tab():
    """Render recommendations with one-click fixes."""
    if not st.session_state.profiles:
        return
    
    st.markdown("### Recommendations & Fixes")
    
    all_recs = []
    for p in st.session_state.profiles:
        for rec in p.recommendations:
            all_recs.append((p.name, rec, p.issues))
    
    if not all_recs:
        st.success("🎉 No issues detected — your data looks clean!")
        return
    
    # Track which fixes to apply
    fixes_to_apply = {}
    
    for i, (col_name, rec, issues) in enumerate(all_recs):
        with st.expander(f"{i+1}. {rec}", expanded=True):
            st.write(f"**Column:** {col_name}")
            if issues:
                st.write("**Issues:**")
                for issue in issues:
                    st.write(f"  - {issue}")
            
            # Determine available fixes
            profile = next(p for p in st.session_state.profiles if p.name == col_name)
            
            fix_options = []
            if profile.null_pct > 50:
                fix_options.append(("drop_nulls", "Drop rows with null values"))
            elif profile.null_pct > 0:
                if profile.dtype == 'numeric':
                    fix_options.append(("impute_median", "Impute nulls with median"))
                else:
                    fix_options.append(("impute_mode", "Impute nulls with mode"))
            
            if profile.dtype == 'numeric' and profile.outlier_pct > 5:
                fix_options.append(("cap_outliers", "Cap outliers at IQR bounds"))
            
            if "date column parsed as string" in " ".join(profile.issues):
                fix_options.append(("cast_date", "Cast to datetime"))
            
            if fix_options:
                selected_fix = st.selectbox(
                    "Apply fix:",
                    options=["Select..."] + [f[1] for f in fix_options],
                    key=f"fix_{col_name}_{i}"
                )
                
                if selected_fix != "Select...":
                    fix_key = [f[0] for f in fix_options if f[1] == selected_fix][0]
                    fixes_to_apply[col_name] = fix_key
    
    # Apply fixes button
    if fixes_to_apply and st.button("Apply Selected Fixes", type="primary"):
        with st.spinner("Applying fixes..."):
            fixed_df = apply_fixes(
                st.session_state.df,
                st.session_state.profiles,
                fixes_to_apply
            )
            st.session_state.df = fixed_df
            # Re-profile
            profiles, qs = profile_dataframe(fixed_df)
            st.session_state.profiles = profiles
            st.session_state.quality_score = qs
            st.session_state.applied_fixes.update(fixes_to_apply)
            st.success(f"Applied {len(fixes_to_apply)} fix(es)! Re-profiling complete.")
            st.rerun()


def render_schema_drift_tab():
    """Render schema drift detection."""
    st.markdown("### Schema Drift Detection")
    
    if st.session_state.baseline_df is None:
        st.info("Upload a baseline CSV to enable schema drift detection.")
        return
    
    if st.session_state.schema_drift is None:
        with st.spinner("Analyzing schema drift..."):
            drift = detect_schema_drift(st.session_state.baseline_df, st.session_state.df)
            st.session_state.schema_drift = drift
    
    drift = st.session_state.schema_drift
    
    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Breaking Changes", len(drift.type_changed) + len(drift.removed_columns))
    with col2:
        st.metric("Warnings", len(drift.added_columns) + len(drift.distribution_shifted))
    with col3:
        st.metric("Common Columns", len(set(st.session_state.baseline_df.columns) & set(st.session_state.df.columns)))
    
    st.markdown(f"**Summary:** {drift.summary}")
    
    if drift.added_columns:
        st.markdown("**Added Columns:**")
        for col in drift.added_columns:
            st.success(f"➕ {col}")
    
    if drift.removed_columns:
        st.markdown("**Removed Columns:**")
        for col in drift.removed_columns:
            st.error(f"➖ {col}")
    
    if drift.type_changed:
        st.markdown("**Type Changes:**")
        for col, old, new in drift.type_changed:
            st.warning(f"🔄 `{col}`: {old} → {new}")
    
    if drift.distribution_shifted:
        st.markdown("**Distribution Shifts (p < 0.05):**")
        for col, p_val in drift.distribution_shifted:
            st.warning(f"📊 `{col}`: p = {p_val:.4f}")


def render_report_tab():
    """Render and download markdown report."""
    if not st.session_state.profiles or st.session_state.quality_score is None:
        return
    
    st.markdown("### Quality Report")
    
    report = generate_markdown_report(
        st.session_state.profiles,
        st.session_state.quality_score,
        st.session_state.schema_drift,
        filename="data.csv"
    )
    
    st.markdown(report)
    
    st.download_button(
        label="📥 Download Report (Markdown)",
        data=report,
        file_name="datalens_quality_report.md",
        mime="text/markdown",
        type="primary"
    )


def main():
    """Main application."""
    # Header with uploads
    uploaded, baseline = render_header()
    
    # Process main file
    if uploaded is not None:
        file_bytes = uploaded.read()
        
        with st.spinner("Loading and profiling CSV..."):
            try:
                df = load_csv(file_bytes)
                st.session_state.df = df
                
                profiles, qs = profile_dataframe(df)
                st.session_state.profiles = profiles
                st.session_state.quality_score = qs
                st.session_state.applied_fixes = {}
                
                # Reset drift if new file
                st.session_state.schema_drift = None
                
            except Exception as e:
                st.error(f"Error loading CSV: {str(e)}")
                return
    
    # Process baseline file
    if baseline is not None and st.session_state.baseline_df is None:
        baseline_bytes = baseline.read()
        try:
            st.session_state.baseline_df = load_csv(baseline_bytes)
            st.session_state.schema_drift = None  # Will recompute
        except Exception as e:
            st.error(f"Error loading baseline: {str(e)}")
    
    # If no data loaded yet
    if st.session_state.df is None:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("👆 Upload a CSV file to get started")
            st.markdown("""
            **DataLens** analyzes your CSV and gives you:
            - 📊 **Quality Score (0-100)** — Single number verdict
            - 🔍 **Column-by-column breakdown** — Heatmap with issues
            - 📈 **Interactive visualizations** — Histograms, box plots, bar charts
            - 🛠️ **One-click fixes** — Impute, cast, dedupe
            - 🔄 **Schema drift detection** — Compare against baseline
            - 📄 **Markdown reports** — Share with your team
            """)
        return
    
    # Tabs for different views
    tabs = st.tabs([
        "📊 Overview",
        "📈 Distributions",
        "🛠️ Recommendations",
        "🔄 Schema Drift",
        "📄 Report"
    ])
    
    with tabs[0]:
        render_quality_overview()
        st.markdown("---")
        render_column_overview()
    
    with tabs[1]:
        render_distribution_tab()
    
    with tabs[2]:
        render_recommendations_tab()
    
    with tabs[3]:
        render_schema_drift_tab()
    
    with tabs[4]:
        render_report_tab()
    
    # Footer stats
    st.markdown("---")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Rows", f"{len(st.session_state.df):,}")
    with cols[1]:
        st.metric("Columns", len(st.session_state.df.columns))
    with cols[2]:
        st.metric("Memory", f"{st.session_state.df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
    with cols[3]:
        st.metric("Fixes Applied", len(st.session_state.applied_fixes))


if __name__ == "__main__":
    main()