import { scoreTextClass, scoreTone } from "@/lib/quality"

const RING_COLORS = {
  excellent: "var(--chart-1)",
  good: "var(--chart-1)",
  warning: "var(--chart-3)",
  poor: "var(--destructive)",
} as const

export function ScoreRing({
  score,
  size = 160,
  children,
}: {
  score: number
  size?: number
  children?: React.ReactNode
}) {
  const tone = scoreTone(score)
  const stroke = RING_COLORS[tone]
  const r = (size - 12) / 2
  const c = 2 * Math.PI * r
  const offset = c - (score / 100) * c

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={8}
          opacity={0.5}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <div
        className={`absolute inset-0 flex flex-col items-center justify-center ${scoreTextClass(score)}`}
      >
        {children}
      </div>
    </div>
  )
}
