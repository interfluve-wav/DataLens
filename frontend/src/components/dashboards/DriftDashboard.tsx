import { motion } from "motion/react"
import {
  AlertTriangle,
  GitCompare,
  Plus,
  Minus,
  ArrowRightLeft,
  TrendingUp,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import type { UploadResponse } from "@/types/datalens"

export function DriftDashboard({ data }: { data: UploadResponse }) {
  const drift = data.schema_drift

  if (!drift) {
    return (
      <div className="flex flex-col gap-6">
        <DashboardHeader
          title="Schema Drift"
          description="Compare this file against a baseline snapshot."
          data={data}
        />
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="size-5" />
              No baseline loaded
            </CardTitle>
            <CardDescription>
              Upload a baseline file (CSV, TSV, Excel, ODS, JSON, or Parquet) with
              your next analysis to detect schema and distribution changes
              automatically.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const breaking =
    drift.type_changed.length + drift.removed_columns.length
  const warnings =
    drift.added_columns.length + drift.distribution_shifted.length

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Schema Drift"
        description={drift.summary}
        data={data}
      />

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          {
            label: "Breaking",
            value: breaking,
            icon: AlertTriangle,
            variant: "destructive" as const,
          },
          {
            label: "Warnings",
            value: warnings,
            icon: TrendingUp,
            variant: "secondary" as const,
          },
          {
            label: "In both versions",
            value: data.column_count - drift.added_columns.length,
            icon: GitCompare,
            variant: "outline" as const,
          },
        ].map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <Card className="glass-panel">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardDescription>{s.label}</CardDescription>
                <s.icon className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <Badge variant={s.variant} className="text-lg px-3 py-1">
                  {s.value}
                </Badge>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <DriftSection
          title="Added Columns"
          icon={Plus}
          items={drift.added_columns.map((c) => c)}
          empty="No new columns"
          tone="primary"
        />
        <DriftSection
          title="Removed Columns"
          icon={Minus}
          items={drift.removed_columns}
          empty="No removed columns"
          tone="destructive"
        />
        <DriftSection
          title="Type Changes"
          icon={ArrowRightLeft}
          items={drift.type_changed.map(
            (t) => `${t.column}: ${t.from} → ${t.to}`,
          )}
          empty="No type changes"
          tone="chart-3"
        />
        <DriftSection
          title="Distribution Shifts"
          icon={TrendingUp}
          items={drift.distribution_shifted.map(
            (d) => `${d.column} (p=${d.p_value.toFixed(4)})`,
          )}
          empty="No significant shifts"
          tone="accent"
        />
      </div>
    </div>
  )
}

function DriftSection({
  title,
  icon: Icon,
  items,
  empty,
}: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  items: string[]
  empty: string
  tone?: string
}) {
  return (
    <Card className="glass-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="size-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{empty}</p>
        ) : (
          items.map((item) => (
            <div
              key={item}
              className="rounded-md border border-border/50 bg-secondary/20 px-3 py-2 text-sm font-mono"
            >
              {item}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}
