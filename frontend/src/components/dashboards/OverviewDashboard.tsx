import { motion } from "motion/react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { ScoreReveal, StaggerChildren } from "@/components/motion/GsapAnimations"
import { ScoreRing } from "@/components/charts/ScoreRing"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import { qualityBadgeVariant, qualityLabel, scoreTextClass } from "@/lib/quality"
import type { UploadResponse } from "@/types/datalens"

export function OverviewDashboard({ data }: { data: UploadResponse }) {
  const { quality_score: qs, issue_summary: issues } = data
  const breakdown = Object.entries(qs.breakdown).filter(([, v]) => v > 0.05)
  const issueTotal = Object.values(issues).reduce((a, b) => a + b, 0)

  const kpis = [
    {
      label: data.is_sampled ? "Rows analyzed" : "Rows",
      value: data.row_count.toLocaleString(),
      sub: data.is_sampled
        ? `of ${(data.total_row_count ?? data.row_count).toLocaleString()} total`
        : undefined,
    },
    { label: "Columns", value: String(data.column_count) },
    { label: "Memory", value: `${data.memory_mb} MB` },
    { label: "Flagged columns", value: String(issueTotal) },
  ]

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Quality Overview"
        description="Your auditable data quality score and what drove it."
        data={data}
      />

      <div className="grid gap-4 lg:grid-cols-[auto_1fr]">
        <Card className="glass-panel glow-primary flex flex-col items-center justify-center p-6">
          <ScoreRing score={qs.overall}>
            <span className={`text-4xl font-bold tabular-nums ${scoreTextClass(qs.overall)}`}>
              <ScoreReveal score={qs.overall} />
            </span>
            <span className="text-xs text-muted-foreground">out of 100</span>
          </ScoreRing>
          <Badge
            variant={qualityBadgeVariant(qs.overall)}
            className="mt-4"
          >
            {qualityLabel(qs.level)}
          </Badge>
        </Card>

        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Penalty breakdown</CardTitle>
            <CardDescription>Factors that reduced the score</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {breakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No significant penalties — data looks clean.
              </p>
            ) : (
              breakdown.map(([key, penalty]) => (
                <div key={key} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono text-destructive">
                      −{penalty.toFixed(1)}
                    </span>
                  </div>
                  <Progress value={Math.min(100, penalty * 4)} className="h-1.5" />
                </div>
              ))
            )}
            <p className="mt-2 border-t border-border/40 pt-3 text-xs text-muted-foreground">
              Weights: nulls 25% · duplicates 20% · outliers 20% · types 15% ·
              cardinality 10% · deep issues 10%
            </p>
          </CardContent>
        </Card>
      </div>

      <StaggerChildren className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <motion.div key={kpi.label} className="stagger-item">
            <Card className="glass-panel transition-colors hover:border-primary/30">
              <CardHeader className="pb-2">
                <CardDescription>{kpi.label}</CardDescription>
                <CardTitle className="text-2xl tabular-nums">{kpi.value}</CardTitle>
                {kpi.sub && (
                  <p className="text-xs text-muted-foreground">{kpi.sub}</p>
                )}
              </CardHeader>
            </Card>
          </motion.div>
        ))}
      </StaggerChildren>

      <Card className="glass-panel">
        <CardHeader>
          <CardTitle>Issue categories</CardTitle>
          <CardDescription>How many columns hit each issue type</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(issues).map(([key, count]) => (
              <div
                key={key}
                className="flex items-center justify-between rounded-lg border border-border/50 bg-secondary/25 px-4 py-3"
              >
                <span className="text-sm capitalize text-muted-foreground">
                  {key.replace(/_/g, " ")}
                </span>
                <span
                  className={`font-mono text-lg font-semibold ${count > 0 ? "text-foreground" : "text-muted-foreground"}`}
                >
                  {count}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
