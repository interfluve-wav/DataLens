import { Loader2 } from "lucide-react"
import { useDataLens } from "@/context/DataLensContext"

export function LoadingOverlay() {
  const { loading, data } = useDataLens()
  if (!loading || !data) return null

  return (
    <div className="pointer-events-auto fixed inset-0 z-50 flex items-start justify-center bg-transparent pt-20">
      <div className="flex items-center gap-2 rounded-full border border-border/60 bg-card/90 px-4 py-2 text-sm shadow-lg backdrop-blur-md">
        <Loader2 className="size-4 animate-spin text-primary" />
        Updating analysis…
      </div>
    </div>
  )
}
