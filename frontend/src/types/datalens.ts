export type QualityLevel =
  | "🟢 Excellent"
  | "🟢 Good"
  | "🟡 Needs Cleaning"
  | "🔴 Poor"

export interface ColumnProfile {
  name: string
  dtype: string
  null_pct: number
  null_count: number
  unique_count: number
  total_count: number
  cardinality: number
  mean?: number | null
  median?: number | null
  std?: number | null
  min_val?: number | null
  max_val?: number | null
  outlier_count: number
  outlier_pct: number
  top_values?: [string, number][] | null
  quality_score: number
  quality_level: QualityLevel
  issues: string[]
  recommendations: string[]
  mixed_type_pct?: number
  invalid_email_count?: number
  encoding_issues?: number
  whitespace_count?: number
  date_format_count?: number
}

export interface QualityScore {
  overall: number
  level: QualityLevel
  breakdown: Record<string, number>
  column_scores: Record<string, number>
}

export interface SchemaDrift {
  added_columns: string[]
  removed_columns: string[]
  type_changed: { column: string; from: string; to: string }[]
  distribution_shifted: { column: string; p_value: number }[]
  summary: string
}

export interface IssueSummary {
  nulls: number
  outliers: number
  mixed_types: number
  email: number
  encoding: number
  whitespace: number
  date_format: number
}

export interface AnalyticsBundle {
  dtype_mix: { name: string; value: number }[]
  null_by_column: { column: string; null_pct: number }[]
  quality_ranking: { column: string; score: number }[]
  penalty_breakdown: { name: string; penalty: number }[]
  issue_mix: { name: string; count: number }[]
  scatter: {
    x_col: string
    y_col: string
    r: number
    points: { x: number; y: number }[]
  } | null
  box_plots: {
    column: string
    min: number
    q1: number
    median: number
    q3: number
    max: number
    outliers: number
  }[]
  row_completeness: { nulls_in_row: number; row_count: number }[]
  health_radar: { metric: string; score: number }[]
  stacked_null: { column: string; valid: number; null: number }[]
  top_categories: { label: string; count: number }[]
}

export interface UploadResponse {
  session_id: string
  filename: string
  row_count: number
  total_row_count?: number
  row_sample_limit?: number | null
  is_sampled?: boolean
  column_count: number
  memory_mb: number
  profiles: ColumnProfile[]
  quality_score: QualityScore
  schema_drift: SchemaDrift | null
  preview: Record<string, string>[]
  correlation: { columns: string[]; matrix: number[][] }
  null_matrix: { column: string; null_pct: number; dtype: string; quality: number }[]
  issue_summary: IssueSummary
  analytics?: AnalyticsBundle
  applied_fixes?: Record<string, string>
}

export interface ColumnDataResponse {
  column: string
  profile: ColumnProfile
  values: (number | string | null)[]
  histogram: { bins: number[]; counts: number[] } | null
  top_values: [string, number][]
}

export type DashboardId =
  | "overview"
  | "columns"
  | "distributions"
  | "analytics"
  | "recommendations"
  | "drift"
  | "correlation"
  | "report"

export const DASHBOARDS: {
  id: DashboardId
  label: string
  description: string
  icon: string
}[] = [
  {
    id: "overview",
    label: "Quality Overview",
    description: "Score gauge, penalties, and KPIs",
    icon: "gauge",
  },
  {
    id: "columns",
    label: "Column Health",
    description: "Heatmap and column diagnostics",
    icon: "grid",
  },
  {
    id: "distributions",
    label: "Distributions",
    description: "Histograms and value analysis",
    icon: "chart",
  },
  {
    id: "analytics",
    label: "BI Analytics",
    description: "Pie, scatter, radar, box plots, and more",
    icon: "layout-dashboard",
  },
  {
    id: "recommendations",
    label: "Fixes",
    description: "Recommendations and one-click fixes",
    icon: "wrench",
  },
  {
    id: "drift",
    label: "Schema Drift",
    description: "Baseline comparison and shifts",
    icon: "git-compare",
  },
  {
    id: "correlation",
    label: "Correlation",
    description: "Numeric relationships and insights",
    icon: "network",
  },
  {
    id: "report",
    label: "Report",
    description: "Exportable markdown quality report",
    icon: "file-text",
  },
]

export const ROW_SAMPLE_PRESETS = [1000, 5000, 10000, 25000, 50000, 100000] as const
