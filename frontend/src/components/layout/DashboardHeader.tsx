import { Badge } from "@/components/ui/badge"
import { FadeIn } from "@/components/motion/GsapAnimations"
import type { UploadResponse } from "@/types/datalens"
import { qualityLabel, effectiveQualityScore } from "@/lib/quality"

export function DatasetContextLine({ data }: { data: UploadResponse }) {
  const total = data.total_row_count ?? data.row_count
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      <span className="truncate font-medium text-foreground/90">{data.filename}</span>
      <span className="text-border">·</span>
      <span>
        {data.is_sampled
          ? `${data.row_count.toLocaleString()} of ${total.toLocaleString()} rows`
          : `${total.toLocaleString()} rows`}
      </span>
      <span className="text-border">·</span>
      <span>{data.column_count} columns</span>
      {data.is_sampled && (
        <Badge variant="outline" className="text-xs">
          Sampled
        </Badge>
      )}
    </div>
  )
}

export function DashboardHeader({
  title,
  description,
  data,
  actions,
}: {
  title: string
  description?: string
  data?: UploadResponse
  actions?: React.ReactNode
}) {
  return (
    <FadeIn>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {title}
          </h1>
          {description && (
            <p className="max-w-2xl text-sm text-muted-foreground sm:text-base">
              {description}
            </p>
          )}
          {data && <DatasetContextLine data={data} />}
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {actions}
          </div>
        )}
      </div>
    </FadeIn>
  )
}

export function QualityScoreChip({ data }: { data: UploadResponse }) {
  const effective = effectiveQualityScore(data)
  return (
    <Badge variant="secondary" className="tabular-nums">
      {effective.overall.toFixed(1)} — {qualityLabel(effective.level)}
    </Badge>
  )
}
