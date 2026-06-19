import type { QualityLevel, UploadResponse } from "@/types/datalens"

/** Prefer profile-weighted score when a sector assessment is present. */
export function effectiveQualityScore(data: UploadResponse): {
  overall: number
  level: QualityLevel
} {
  if (data.profile_assessment) {
    return {
      overall: data.profile_assessment.overall,
      level: data.profile_assessment.level,
    }
  }
  return {
    overall: data.quality_score.overall,
    level: data.quality_score.level,
  }
}

/** Strip leading emoji from profiler quality labels. */
export function qualityLabel(level: QualityLevel | string): string {
  return level.replace(/^[\s\p{Emoji_Presentation}\p{Extended_Pictographic}]+\s*/u, "").trim()
}

export function scoreTone(score: number): "excellent" | "good" | "warning" | "poor" {
  if (score >= 90) return "excellent"
  if (score >= 70) return "good"
  if (score >= 50) return "warning"
  return "poor"
}

export function scoreTextClass(score: number): string {
  const tone = scoreTone(score)
  if (tone === "excellent" || tone === "good") return "text-primary"
  if (tone === "warning") return "text-chart-3"
  return "text-destructive"
}

export function scoreHeatClass(score: number): string {
  const tone = scoreTone(score)
  if (tone === "excellent") return "bg-primary/15 text-primary"
  if (tone === "good") return "bg-primary/10 text-primary"
  if (tone === "warning") return "bg-chart-3/15 text-chart-3"
  return "bg-destructive/15 text-destructive"
}

export function qualityBadgeVariant(
  score: number,
): "default" | "secondary" | "outline" | "destructive" {
  const tone = scoreTone(score)
  if (tone === "excellent") return "default"
  if (tone === "good") return "secondary"
  if (tone === "warning") return "outline"
  return "destructive"
}
