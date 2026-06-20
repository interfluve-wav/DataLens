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
import { useDataLens } from "@/context/DataLensContext"
import { getColumnData } from "@/lib/api"
import type { ColumnDataResponse, UploadResponse } from "@/types/datalens"

const tooltipStyle = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-full min-h-48 items-center justify-center text-sm text-muted-foreground">
      {message}
    </div>
  )
}

export function DistributionsDashboard({ data }: { data: UploadResponse }) {
  const { loading: sessionLoading } = useDataLens()
  const columns = data.profiles
  const columnNamesKey = columns.map((p) => p.name).join("\0")
  const [selected, setSelected] = useState(() => columns[0]?.name ?? "")
  const [columnData, setColumnData] = useState<ColumnDataResponse | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const names = columnNamesKey ? columnNamesKey.split("\0") : []
    if (names.length === 0) {
      setSelected("")
      return
    }
    setSelected((current) => (names.includes(current) ? current : names[0]))
  }, [columnNamesKey])

  useEffect(() => {
    if (!selected) return
    let cancelled = false
    setLoading(true)
    setLoadError(false)
    getColumnData(data.session_id, selected)
      .then((result) => {
        if (!cancelled) setColumnData(result)
      })
      .catch(() => {
        if (!cancelled) {
          setColumnData(null)
          setLoadError(true)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [data.session_id, data.revision, selected])

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

  const selectedMeta = columns.find((p) => p.name === selected)
  const isNumeric = profile?.dtype === "numeric"

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Distributions"
        description="Histograms and top-value charts per column."
        data={data}
      />

      {columns.length === 0 ? (
        <Card className="glass-panel">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No columns in this dataset.
          </CardContent>
        </Card>
      ) : (
        <>
          {profile && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "Null %", value: `${profile.null_pct.toFixed(1)}%` },
                {
                  label: "Unique",
                  value: profile.unique_count.toLocaleString(),
                },
                {
                  label: "Mean",
                  value: profile.mean != null ? profile.mean.toFixed(2) : "—",
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
          )}

          <Card className="glass-panel">
            <CardHeader className="gap-4 border-b border-border/40 pb-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex flex-col gap-1">
                  <CardTitle>
                    {isNumeric ? "Histogram" : profile ? "Top Values" : "Distribution"}
                  </CardTitle>
                  <CardDescription className="flex flex-wrap items-center gap-2">
                    <span>{selected || "Select a column"}</span>
                    {selectedMeta && (
                      <Badge variant="outline">{selectedMeta.dtype}</Badge>
                    )}
                  </CardDescription>
                </div>
                <div className="flex w-full flex-col gap-1.5 lg:w-72 lg:shrink-0">
                  <Label htmlFor="dist-column" className="text-xs text-muted-foreground">
                    Column
                  </Label>
                  <Select
                    value={selected}
                    onValueChange={setSelected}
                    disabled={sessionLoading || loading}
                  >
                    <SelectTrigger id="dist-column" className="w-full">
                      <SelectValue placeholder="Choose a column…" />
                    </SelectTrigger>
                    <SelectContent align="end" className="max-h-72">
                      <SelectGroup>
                        {columns.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.name} ({p.dtype})
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
                <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-background/40 backdrop-blur-[1px]">
                  <Loader2 className="size-5 animate-spin text-muted-foreground" />
                </div>
              )}
              <div
                className="size-full outline-none [&_.recharts-surface]:outline-none [&_.recharts-wrapper]:outline-none"
                style={{ opacity: loading ? 0.55 : 1, transition: "opacity 0.15s" }}
              >
                {loadError ? (
                  <EmptyChart message="Failed to load column data" />
                ) : !profile && !loading ? (
                  <EmptyChart message="Select a column to view its distribution" />
                ) : isNumeric && histData.length === 0 ? (
                  <EmptyChart message="No numeric values to chart (all null or unparseable)" />
                ) : isNumeric && histData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
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
                  </ResponsiveContainer>
                ) : catData.length === 0 ? (
                  <EmptyChart message="No values to chart" />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
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
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>

          {profile && profile.issues.length > 0 && (
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
      )}
    </div>
  )
}
