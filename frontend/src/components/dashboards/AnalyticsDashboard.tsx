import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import { ChartPanel } from "@/components/charts/ChartPanel"
import {
  CHART_COLORS,
  axisTick,
  chartMargin,
  tooltipStyle,
} from "@/lib/chart-theme"
import type { AnalyticsBundle, UploadResponse } from "@/types/datalens"

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-full min-h-48 items-center justify-center text-sm text-muted-foreground">
      {message}
    </div>
  )
}

function BoxPlotStrip({
  box,
}: {
  box: {
    column: string
    min: number
    q1: number
    median: number
    q3: number
    max: number
    outliers: number
  }
}) {
  const span = box.max - box.min || 1
  const pct = (v: number) => `${((v - box.min) / span) * 100}%`
  const iqrLeft = pct(box.q1)
  const iqrWidth = `${((box.q3 - box.q1) / span) * 100}%`
  const medLeft = pct(box.median)

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="truncate font-medium">{box.column}</span>
        <span className="shrink-0 font-mono text-muted-foreground">
          med {box.median.toFixed(2)}
        </span>
      </div>
      <div className="relative h-6 rounded-md bg-secondary/40">
        <div
          className="absolute top-1/2 h-px w-full -translate-y-1/2 bg-border"
          style={{ left: 0 }}
        />
        <div
          className="absolute top-1/2 h-4 -translate-y-1/2 rounded-sm bg-primary/35 border border-primary/50"
          style={{ left: iqrLeft, width: iqrWidth }}
        />
        <div
          className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary"
          style={{ left: medLeft }}
        />
      </div>
      <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>{box.min.toFixed(1)}</span>
        <span>{box.outliers} outliers</span>
        <span>{box.max.toFixed(1)}</span>
      </div>
    </div>
  )
}

export function AnalyticsDashboard({ data }: { data: UploadResponse }) {
  const a: AnalyticsBundle | undefined = data.analytics

  if (!a) {
    return (
      <div className="flex flex-col gap-6">
        <DashboardHeader
          title="BI Analytics"
          description="Composition, completeness, and correlation charts."
          data={data}
        />
        <EmptyChart message="Re-upload your CSV to load analytics charts." />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="BI Analytics"
        description="Pie, scatter, radar, box plots, and completeness views."
        data={data}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartPanel title="Column types" description="Numeric vs categorical mix">
          {a.dtype_mix.length === 0 ? (
            <EmptyChart message="No columns" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={a.dtype_mix}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius="55%"
                  outerRadius="80%"
                  paddingAngle={2}
                  isAnimationActive={false}
                >
                  {a.dtype_mix.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>

        <ChartPanel
          title="Issue categories"
          description="Columns affected per issue type"
        >
          {a.issue_mix.length === 0 ? (
            <EmptyChart message="No issues detected" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={a.issue_mix}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius="80%"
                  isAnimationActive={false}
                >
                  {a.issue_mix.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>

        <ChartPanel
          title="Null rate by column"
          description="Top columns with missing data"
          className="lg:col-span-2 h-auto [&>div:last-child]:h-72"
        >
          {a.null_by_column.length === 0 ? (
            <EmptyChart message="No null values" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={a.null_by_column}
                layout="vertical"
                margin={{ ...chartMargin, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                <XAxis type="number" unit="%" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="column"
                  type="category"
                  width={100}
                  tick={{ ...axisTick, fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Bar dataKey="null_pct" fill="var(--chart-4)" radius={[0, 4, 4, 0]} maxBarSize={20} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>

        <ChartPanel
          title="Quality ranking"
          description="Column scores (lowest first)"
          className="lg:col-span-2 h-auto [&>div:last-child]:h-72"
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={a.quality_ranking}
              layout="vertical"
              margin={{ ...chartMargin, left: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
              <XAxis type="number" domain={[0, 100]} tick={axisTick} axisLine={false} tickLine={false} />
              <YAxis
                dataKey="column"
                type="category"
                width={100}
                tick={{ ...axisTick, fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip cursor={false} contentStyle={tooltipStyle} />
              <Bar dataKey="score" fill="var(--chart-1)" radius={[0, 4, 4, 0]} maxBarSize={20} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Completeness stack"
          description="Valid vs null % (top nullable columns)"
        >
          {a.stacked_null.length === 0 ? (
            <EmptyChart message="No nullable columns" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={a.stacked_null} margin={chartMargin}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                <XAxis dataKey="column" tick={{ ...axisTick, fontSize: 9 }} angle={-25} textAnchor="end" height={56} />
                <YAxis unit="%" tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Legend />
                <Bar dataKey="valid" stackId="a" fill="var(--chart-1)" isAnimationActive={false} />
                <Bar dataKey="null" stackId="a" fill="var(--chart-4)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>

        <ChartPanel
          title="Score penalties"
          description="What reduced the overall quality score"
        >
          {a.penalty_breakdown.length === 0 ? (
            <EmptyChart message="No penalties" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={a.penalty_breakdown} margin={chartMargin}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ ...axisTick, fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Bar dataKey="penalty" fill="var(--chart-4)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>

        <ChartPanel
          title="Dataset health radar"
          description="Normalized dimension scores (0–100)"
        >
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={a.health_radar} cx="50%" cy="50%" outerRadius="70%">
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="metric" tick={{ ...axisTick, fontSize: 10 }} />
              <Radar
                dataKey="score"
                stroke="var(--chart-1)"
                fill="var(--chart-1)"
                fillOpacity={0.25}
                isAnimationActive={false}
              />
              <Tooltip cursor={false} contentStyle={tooltipStyle} />
            </RadarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Row completeness"
          description="How many null fields per row"
        >
          {a.row_completeness.length === 0 ? (
            <EmptyChart message="No row data" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={a.row_completeness} margin={chartMargin}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                <XAxis dataKey="nulls_in_row" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Area
                  type="monotone"
                  dataKey="row_count"
                  stroke="var(--chart-2)"
                  fill="var(--chart-2)"
                  fillOpacity={0.2}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartPanel>

        {a.scatter && a.scatter.points.length > 0 ? (
          <ChartPanel
            title="Correlation scatter"
            description={`${a.scatter.x_col} vs ${a.scatter.y_col} (r=${a.scatter.r.toFixed(2)})`}
            className="lg:col-span-2 h-auto [&>div:last-child]:h-80"
          >
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name={a.scatter.x_col}
                  tick={axisTick}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name={a.scatter.y_col}
                  tick={axisTick}
                  axisLine={false}
                  tickLine={false}
                />
                <ZAxis range={[40, 40]} />
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Scatter
                  data={a.scatter.points}
                  fill="var(--chart-1)"
                  fillOpacity={0.55}
                  isAnimationActive={false}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </ChartPanel>
        ) : null}

        {a.box_plots.length > 0 ? (
          <ChartPanel
            title="Box plot summary"
            description="IQR, median, and whiskers for numeric columns"
            className="lg:col-span-2 h-auto"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              {a.box_plots.map((box) => (
                <BoxPlotStrip key={box.column} box={box} />
              ))}
            </div>
          </ChartPanel>
        ) : null}

        {a.top_categories.length > 0 ? (
          <ChartPanel
            title="Top categorical values"
            description="Most frequent values across text columns"
            className="lg:col-span-2 h-auto [&>div:last-child]:h-72"
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={a.top_categories} margin={chartMargin}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                <XAxis dataKey="label" tick={{ ...axisTick, fontSize: 8 }} angle={-30} textAnchor="end" height={70} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip cursor={false} contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill="var(--chart-3)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        ) : null}
      </div>
    </div>
  )
}
