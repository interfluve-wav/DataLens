import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import { qualityBadgeVariant, qualityLabel, scoreHeatClass } from "@/lib/quality"
import type { ColumnProfile, UploadResponse } from "@/types/datalens"

export function ColumnsDashboard({ data }: { data: UploadResponse }) {
  const [query, setQuery] = useState("")

  const sorted = useMemo(
    () => [...data.profiles].sort((a, b) => a.quality_score - b.quality_score),
    [data.profiles],
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return sorted
    return sorted.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.dtype.includes(q) ||
        p.issues.some((i) => i.toLowerCase().includes(q)),
    )
  }, [sorted, query])

  const avgNull =
    data.profiles.reduce((s, p) => s + p.null_pct, 0) /
    Math.max(data.profiles.length, 1)

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Column Health"
        description={
          data.profile_assessment
            ? "Per-column profiler scores (legacy model), sorted worst-first."
            : "Per-column diagnostics sorted worst-first. Search to filter."
        }
        data={data}
      />

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: "Avg null %", value: `${avgNull.toFixed(1)}%` },
          {
            label: "Needs attention",
            value: sorted.filter((p) => p.quality_score < 70).length.toString(),
          },
          {
            label: "Excellent",
            value: sorted.filter((p) => p.quality_score >= 90).length.toString(),
          },
        ].map((stat) => (
          <Card key={stat.label} className="glass-panel">
            <CardHeader className="pb-2">
              <CardDescription>{stat.label}</CardDescription>
              <CardTitle className="text-2xl tabular-nums">{stat.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card className="glass-panel">
        <CardHeader className="gap-4 border-b border-border/40 pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Column heatmap</CardTitle>
              <CardDescription>
                {filtered.length} of {sorted.length} columns
              </CardDescription>
            </div>
            <div className="relative w-full sm:max-w-xs">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search columns…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[min(60vh,520px)]">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="sticky top-0 z-10 bg-card">Column</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Type</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Null %</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Unique</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card text-right">Score</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Status</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-card">Issues</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                      No columns match your search.
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((p: ColumnProfile) => (
                    <TableRow key={p.name} className="hover:bg-secondary/30">
                      <TableCell className="max-w-[140px] truncate font-medium">
                        {p.name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{p.dtype}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {p.null_pct.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {p.unique_count.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={`inline-flex rounded-md px-2 py-0.5 font-mono text-sm font-semibold ${scoreHeatClass(p.quality_score)}`}
                        >
                          {p.quality_score.toFixed(0)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={qualityBadgeVariant(p.quality_score)} className="text-xs">
                          {qualityLabel(p.quality_level)}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                        {p.issues.join(" · ") || "—"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}
