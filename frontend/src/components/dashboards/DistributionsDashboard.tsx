import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import { getColumnData } from "@/lib/api"
import type { ColumnDataResponse, UploadResponse } from "@/types/datalens"

const tooltipStyle = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
}

export function DistributionsDashboard({ data }: { data: UploadResponse }) {
  const [selected, setSelected] = useState(data.profiles[0]?.name ?? "")
  const [columnData, setColumnData] = useState<ColumnDataResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!selected) return
    let cancelled = false
    setLoading(true)
    getColumnData(data.session_id, selected)
      .then((result) => {
        if (!cancelled) setColumnData(result)
      })
      .catch(() => {
        if (!cancelled) setColumnData(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [data.session_id, data.row_count, selected])

  const profile = columnData?.profile
  const histData =
    columnData?.histogram?.bins.map((bin, i) => ({
      bin: bin.toFixed(1),
      count: columnData.histogram!.counts[i],
    })) ?? []

  const catData =
    columnData?.top_values?.map(([value, count]) => ({
      value: String(value).slice(0, 24),
      count,
    })) ?? []

  const selectedMeta = data.profiles.find((p) => p.name === selected)

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Distributions"
        description="Histograms and top-value charts per column."
        data={data}
      />

      {profile ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Null %", value: `${profile.null_pct.toFixed(1)}%` },
              {
                label: "Unique",
                value: profile.unique_count.toLocaleString(),
              },
              {
                label: "Mean",
                value:
                  profile.mean != null ? profile.mean.toFixed(2) : "—",
              },
              {
                label: "Outliers",
                value:
                  profile.dtype === "numeric"
                    ? `${profile.outlier_pct.toFixed(1)}%`
                    : "—",
              },
            ].map((s) => (
              <Card key={s.label} className="glass-panel">
                <CardHeader className="pb-2">
                  <CardDescription>{s.label}</CardDescription>
                  <CardTitle>{s.value}</CardTitle>
                </CardHeader>
              </Card>
            ))}
          </div>

          <Card className="glass-panel">
            <CardHeader className="gap-4 border-b border-border/40 pb-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex flex-col gap-1">
                  <CardTitle>
                    {profile.dtype === "numeric" ? "Histogram" : "Top Values"}
                  </CardTitle>
                  <CardDescription className="flex flex-wrap items-center gap-2">
                    <span>{selected}</span>
                    {selectedMeta && (
                      <Badge variant="outline">{selectedMeta.dtype}</Badge>
                    )}
                  </CardDescription>
                </div>
                <div className="flex w-full flex-col gap-1.5 lg:w-72 lg:shrink-0">
                  <Label htmlFor="dist-column" className="text-xs text-muted-foreground">
                    Column
                  </Label>
                  <Select value={selected} onValueChange={setSelected}>
                    <SelectTrigger id="dist-column" className="w-full">
                      <SelectValue placeholder="Choose a column…" />
                    </SelectTrigger>
                    <SelectContent position="popper" align="end">
                      <SelectGroup>
                        {data.profiles.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.name}
                            <span className="ml-2 text-muted-foreground">({p.dtype})</span>
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="relative h-80 pt-4">
              {loading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-background/40 backdrop-blur-[1px]">
                  <Loader2 className="size-5 animate-spin text-muted-foreground" />
                </div>
              )}
              <div
                className="size-full outline-none [&_.recharts-surface]:outline-none [&_.recharts-wrapper]:outline-none"
                style={{ opacity: loading ? 0.55 : 1, transition: "opacity 0.15s" }}
              >
                <ResponsiveContainer width="100%" height="100%">
                  {profile.dtype === "numeric" && histData.length > 0 ? (
                    <BarChart data={histData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                      <XAxis
                        dataKey="bin"
                        tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        cursor={false}
                        contentStyle={tooltipStyle}
                        labelStyle={{ color: "var(--foreground)" }}
                      />
                      <Bar
                        dataKey="count"
                        fill="var(--chart-1)"
                        radius={[4, 4, 0, 0]}
                        maxBarSize={48}
                        isAnimationActive={false}
                      />
                    </BarChart>
                  ) : (
                    <BarChart
                      data={catData}
                      layout="vertical"
                      margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="var(--border)" />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={false}
                      />
                      <YAxis
                        dataKey="value"
                        type="category"
                        width={120}
                        tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip cursor={false} contentStyle={tooltipStyle} />
                      <Bar
                        dataKey="count"
                        fill="var(--chart-1)"
                        radius={[0, 4, 4, 0]}
                        maxBarSize={32}
                        isAnimationActive={false}
                      />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {profile.issues.length > 0 && (
            <Card className="glass-panel border-destructive/30">
              <CardHeader>
                <CardTitle>Detected Issues</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {profile.issues.map((issue) => (
                  <Badge key={issue} variant="destructive">
                    {issue}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      ) : loading ? (
        <Card className="glass-panel flex h-80 items-center justify-center">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </Card>
      ) : null}
    </div>
  )
}
