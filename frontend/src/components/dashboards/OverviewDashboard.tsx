import { motion } from "motion/react"
import { CheckCircle2, XCircle } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ScoreReveal, StaggerChildren } from "@/components/motion/GsapAnimations"
import { ScoreRing } from "@/components/charts/ScoreRing"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import {
  effectiveQualityScore,
  qualityBadgeVariant,
  qualityLabel,
  scoreTextClass,
} from "@/lib/quality"
import type { UploadResponse } from "@/types/datalens"
import { AiReviewPanel, RuleSampleFailures } from "@/components/dashboards/AiReviewPanel"

export function OverviewDashboard({
  data,
  onDataUpdate,
}: {
  data: UploadResponse
  onDataUpdate?: (next: UploadResponse) => void
}) {
  const { quality_score: qs, issue_summary: issues, profile_assessment: pa } = data
  const effective = effectiveQualityScore(data)
  const breakdown = Object.entries(qs.breakdown).filter(([, v]) => v > 0.05)

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
    {
      label: "Contract rules",
      value: pa ? `${pa.rules_passed}/${pa.rules_total}` : "—",
      sub: pa ? (pa.contract_passed ? "All critical passed" : "Critical failures") : undefined,
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Quality Overview"
        description={
          pa
            ? `${pa.profile_label} profile — weighted dimension score with contract checks.`
            : "Your auditable data quality score and what drove it."
        }
        data={data}
      />

      {pa && (
        <Card className="glass-panel border-primary/20">
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base">{pa.profile_label}</CardTitle>
              <Badge variant={pa.contract_passed ? "secondary" : "destructive"}>
                {pa.contract_passed ? "Contract passed" : "Contract failed"}
              </Badge>
            </div>
            <CardDescription className="text-xs">{pa.source}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            {pa.required_columns.length > 0 ? (
              <span>
                Required:{" "}
                <span className="font-mono text-foreground">
                  {pa.required_columns.join(", ")}
                </span>
              </span>
            ) : (
              <span>No required columns resolved (auto-detect or specify at upload).</span>
            )}
            {pa.missing_required_columns.length > 0 && (
              <span className="text-destructive">
                Missing: {pa.missing_required_columns.join(", ")}
              </span>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-[auto_1fr]">
        <Card className="glass-panel glow-primary flex flex-col items-center justify-center p-6">
          <ScoreRing score={effective.overall}>
            <span
              className={`text-4xl font-bold tabular-nums ${scoreTextClass(effective.overall)}`}
            >
              <ScoreReveal score={effective.overall} />
            </span>
            <span className="text-xs text-muted-foreground">out of 100</span>
          </ScoreRing>
          <Badge variant={qualityBadgeVariant(effective.overall)} className="mt-4">
            {qualityLabel(effective.level)}
          </Badge>
        </Card>

        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>
              {pa ? "Dimension scores" : "Penalty breakdown"}
            </CardTitle>
            <CardDescription>
              {pa
                ? "Weighted contributions from the selected profile"
                : "Factors that reduced the score"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {pa ? (
              pa.dimension_scores.map((d) => (
                <div key={d.dimension} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize">{d.dimension.replace(/_/g, " ")}</span>
                    <span className="font-mono text-muted-foreground">
                      {(d.weight * 100).toFixed(0)}% · {d.score.toFixed(1)}
                    </span>
                  </div>
                  <Progress value={d.score} className="h-1.5" />
                </div>
              ))
            ) : breakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No significant penalties — data looks clean.
              </p>
            ) : (
              breakdown.map(([key, penalty]) => (
                <div key={key} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono text-destructive">−{penalty.toFixed(1)}</span>
                  </div>
                  <Progress value={Math.min(100, penalty * 4)} className="h-1.5" />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {pa && pa.rules.length > 0 && (
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Data quality contract</CardTitle>
            <CardDescription>
              Pass/fail rules for this profile ({pa.rules_passed} of {pa.rules_total} passed)
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10" />
                  <TableHead>Rule</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead className="text-right">Violations</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pa.rules.map((rule) => (
                  <TableRow key={rule.rule_id}>
                    <TableCell>
                      {rule.passed ? (
                        <CheckCircle2 className="size-4 text-primary" />
                      ) : (
                        <XCircle className="size-4 text-destructive" />
                      )}
                    </TableCell>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs capitalize">
                        {rule.severity}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs text-sm text-muted-foreground">
                      <div>{rule.message}</div>
                      {!rule.passed && rule.sample_failures?.length > 0 && (
                        <RuleSampleFailures
                          ruleId={rule.rule_id}
                          samples={rule.sample_failures}
                        />
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {rule.violation_count > 0
                        ? `${rule.violation_count} (${rule.violation_pct}%)`
                        : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {onDataUpdate && <AiReviewPanel data={data} onUpdate={onDataUpdate} />}

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
