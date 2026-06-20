import { useState } from "react"
import { Brain, ChevronDown, ChevronRight, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { runLlmVerify } from "@/lib/api"
import type { LlmVerificationResult, UploadResponse } from "@/types/datalens"

export function AiReviewPanel({
  data,
  onUpdate,
}: {
  data: UploadResponse
  onUpdate: (next: UploadResponse) => void
}) {
  const [loading, setLoading] = useState(false)
  const verification = data.llm_verification
  const stale = data.llm_verification_stale

  if (!data.llm_available) {
    return null
  }

  const handleRun = async () => {
    setLoading(true)
    try {
      const next = await runLlmVerify(data.session_id)
      onUpdate(next)
      toast.success("AI review complete")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "AI review failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="glass-panel border-chart-4/30">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Brain className="size-4 text-chart-4" />
            <CardTitle className="text-base">AI semantic review</CardTitle>
          </div>
          <Button size="sm" variant="outline" onClick={handleRun} disabled={loading}>
            {loading ? (
              <Loader2 className="size-4 animate-spin" data-icon="inline-start" />
            ) : (
              <Brain data-icon="inline-start" />
            )}
            {verification && !stale ? "Re-run review" : "Run AI review"}
          </Button>
        </div>
        <CardDescription>
          Interprets profiler summaries and sample rows — not your full dataset.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {stale && verification && (
          <p className="text-sm text-chart-3">
            Results are from revision {data.llm_verification_revision}; data changed at
            revision {data.revision}. Re-run to refresh.
          </p>
        )}
        {!verification ? (
          <p className="text-sm text-muted-foreground">
            Run a review to triage contract failures and survey-style flags with cited
            evidence from deterministic profiling.
          </p>
        ) : (
          <VerificationResults result={verification} />
        )}
      </CardContent>
    </Card>
  )
}

function VerificationResults({ result }: { result: LlmVerificationResult }) {
  return (
    <div className="flex flex-col gap-4">
      {result.summary && (
        <p className="text-sm text-muted-foreground">{result.summary}</p>
      )}
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">{result.model_id}</Badge>
        <Badge variant="outline">
          Confidence {(result.verification_confidence * 100).toFixed(0)}%
        </Badge>
      </div>

      {result.confirmed_issues.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-medium">Confirmed for review</h4>
          {result.confirmed_issues.map((issue) => (
            <div
              key={issue.issue_id}
              className="rounded-lg border border-border/50 bg-secondary/20 px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{issue.title}</span>
                <Badge variant="outline" className="text-xs capitalize">
                  {issue.severity}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {issue.suggested_action.replace(/_/g, " ")}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{issue.explanation}</p>
              {issue.evidence_refs.length > 0 && (
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {issue.evidence_refs.join(" · ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {result.rejected_false_positives.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-medium">Rejected false positives</h4>
          {result.rejected_false_positives.map((fp) => (
            <div
              key={fp.candidate_id}
              className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm text-muted-foreground"
            >
              {fp.reason}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function RuleSampleFailures({
  ruleId,
  samples,
}: {
  ruleId: string
  samples: Record<string, unknown>[]
}) {
  const [open, setOpen] = useState(false)
  if (!samples.length) return null

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-primary hover:underline"
      >
        {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        {samples.length} sample row{samples.length === 1 ? "" : "s"}
      </button>
      {open && (
        <pre className="mt-1 max-h-40 overflow-auto rounded-md bg-secondary/40 p-2 text-xs">
          {JSON.stringify(samples, null, 2)}
        </pre>
      )}
      <span className="sr-only">Sample failures for rule {ruleId}</span>
    </div>
  )
}
