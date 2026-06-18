import { useMemo } from "react"
import { motion } from "motion/react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import type { UploadResponse } from "@/types/datalens"

function corrColor(value: number) {
  if (value >= 0.7) return "bg-primary/80 text-primary-foreground"
  if (value >= 0.4) return "bg-primary/40"
  if (value <= -0.7) return "bg-destructive/80 text-destructive-foreground"
  if (value <= -0.4) return "bg-destructive/40"
  return "bg-muted/50"
}

export function CorrelationDashboard({ data }: { data: UploadResponse }) {
  const { columns, matrix } = data.correlation

  const strongPairs = useMemo(() => {
    const pairs: { a: string; b: string; r: number }[] = []
    for (let i = 0; i < columns.length; i++) {
      for (let j = i + 1; j < columns.length; j++) {
        const r = matrix[i]?.[j] ?? 0
        if (Math.abs(r) >= 0.5) {
          pairs.push({ a: columns[i], b: columns[j], r })
        }
      }
    }
    return pairs.sort((x, y) => Math.abs(y.r) - Math.abs(x.r)).slice(0, 8)
  }, [columns, matrix])

  if (columns.length < 2) {
    return (
      <div className="flex flex-col gap-6">
        <DashboardHeader
          title="Correlation"
          description="Pearson relationships between numeric columns."
          data={data}
        />
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle>Not enough numeric data</CardTitle>
            <CardDescription>
              Need at least two numeric columns with sufficient values for
              correlation analysis.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Correlation"
        description="Heatmap and strong pairs (|r| ≥ 0.5) across numeric columns."
        data={data}
      />

      {strongPairs.length > 0 && (
          <Card className="glass-panel">
            <CardHeader>
              <CardTitle>Strong Relationships</CardTitle>
              <CardDescription>|r| ≥ 0.5</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {strongPairs.map((p) => (
                <motion.div
                  key={`${p.a}-${p.b}`}
                  whileHover={{ scale: 1.03 }}
                  className="rounded-lg border border-border/60 bg-secondary/30 px-4 py-2 text-sm"
                >
                  <span className="font-medium">{p.a}</span>
                  <span className="mx-2 text-muted-foreground">↔</span>
                  <span className="font-medium">{p.b}</span>
                  <span className="ml-2 font-mono text-primary">
                    r={p.r.toFixed(2)}
                  </span>
                </motion.div>
              ))}
            </CardContent>
          </Card>
      )}

      <Card className="glass-panel overflow-hidden">
          <CardHeader>
            <CardTitle>Correlation Heatmap</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr>
                  <th className="p-2 text-left" />
                  {columns.map((c) => (
                    <th
                      key={c}
                      className="max-w-20 truncate p-2 text-left font-medium"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {columns.map((row, i) => (
                  <tr key={row}>
                    <td className="max-w-24 truncate p-2 font-medium">
                      {row}
                    </td>
                    {columns.map((_, j) => {
                      const v = matrix[i]?.[j] ?? 0
                      return (
                        <td key={`${i}-${j}`} className="p-1">
                          <div
                            className={`flex size-10 items-center justify-center rounded-md font-mono text-[10px] ${corrColor(v)}`}
                            title={`${row} vs ${columns[j]}: ${v.toFixed(2)}`}
                          >
                            {v.toFixed(1)}
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
    </div>
  )
}
