import { useEffect, useState } from "react"
import { Download } from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import { getReport } from "@/lib/api"
import type { UploadResponse } from "@/types/datalens"

export function ReportDashboard({ data }: { data: UploadResponse }) {
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [filename, setFilename] = useState("datalens_report.md")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getReport(data.session_id)
      .then((r) => {
        setMarkdown(r.markdown)
        setFilename(r.filename)
      })
      .catch(() => toast.error("Failed to load report"))
      .finally(() => setLoading(false))
  }, [data.session_id, data.quality_score.overall])

  const download = () => {
    if (!markdown) return
    const blob = new Blob([markdown], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    toast.success("Report downloaded")
  }

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Quality Report"
        description="Markdown summary for tickets and handoffs."
        data={data}
        actions={
          <Button onClick={download} disabled={!markdown || loading}>
            <Download data-icon="inline-start" />
            Download
          </Button>
        }
      />

      <Card className="glass-panel">
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          <CardDescription>{filename}</CardDescription>
        </CardHeader>
        <CardContent>
            {loading ? (
              <Skeleton className="h-96 w-full" />
            ) : (
              <ScrollArea className="h-[min(70vh,600px)] rounded-lg border border-border/60 bg-secondary/20 p-4">
                <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
                  {markdown}
                </pre>
              </ScrollArea>
            )}
          </CardContent>
      </Card>
    </div>
  )
}
