import { useCallback, useState } from "react"
import { FileSpreadsheet, Upload, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileChip({
  file,
  onClear,
}: {
  file: File
  onClear: () => void
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-secondary/40 px-3 py-2 text-sm">
      <FileSpreadsheet className="size-4 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{file.name}</p>
        <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className="shrink-0"
        onClick={onClear}
        aria-label={`Remove ${file.name}`}
      >
        <X />
      </Button>
    </div>
  )
}

export function FileDropzone({
  id,
  label,
  hint,
  file,
  onFile,
  optional,
}: {
  id: string
  label: string
  hint?: string
  file: File | null
  onFile: (file: File | null) => void
  optional?: boolean
}) {
  const [dragOver, setDragOver] = useState(false)

  const pick = useCallback(
    (f: File | null) => {
      if (f && !f.name.toLowerCase().endsWith(".csv")) return
      onFile(f)
    },
    [onFile],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      pick(e.dataTransfer.files?.[0] ?? null)
    },
    [pick],
  )

  if (file) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">
          {label}
          {optional && (
            <span className="ml-1 font-normal text-muted-foreground">(optional)</span>
          )}
        </span>
        <FileChip file={file} onClear={() => onFile(null)} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">
        {label}
        {optional && (
          <span className="ml-1 font-normal text-muted-foreground">(optional)</span>
        )}
      </span>
      <label
        htmlFor={id}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border/70 bg-secondary/20 hover:border-primary/40 hover:bg-secondary/30",
        )}
      >
        <Upload className="size-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Drop CSV here or <span className="text-primary">browse</span>
        </span>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
        <input
          id={id}
          type="file"
          accept=".csv"
          className="sr-only"
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />
      </label>
    </div>
  )
}
