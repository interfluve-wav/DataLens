import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import { Loader2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FadeIn } from "@/components/motion/GsapAnimations"
import { FileDropzone } from "@/components/layout/FileDropzone"
import { useDataLens } from "@/context/DataLensContext"

const FEATURES = [
  { title: "Quality score", detail: "Single 0–100 verdict with penalty breakdown" },
  { title: "8 dashboards", detail: "Columns, distributions, BI charts, drift & more" },
  { title: "One-click fixes", detail: "Impute, strip, and drop with instant re-profile" },
]

export function UploadHero() {
  const { upload, loading, error } = useDataLens()
  const [file, setFile] = useState<File | null>(null)
  const [baseline, setBaseline] = useState<File | null>(null)

  const handleSubmit = async () => {
    if (!file) return
    await upload(file, baseline)
  }

  return (
    <div className="mesh-bg flex min-h-svh flex-col items-center justify-center px-4 py-12 sm:py-16">
      <FadeIn className="flex w-full max-w-xl flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/15 glow-primary">
            <Sparkles className="size-7 text-primary" />
          </div>
          <div className="flex flex-col gap-2">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Data<span className="text-primary">Lens</span>
            </h1>
            <p className="text-base text-muted-foreground sm:text-lg">
              Score, diagnose, and fix CSV quality before it hits your pipeline.
            </p>
          </div>
        </div>

        <Card className="glass-panel w-full">
          <CardHeader>
            <CardTitle>Upload CSV</CardTitle>
            <CardDescription>
              Add an optional baseline file to enable schema drift detection.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <FileDropzone
              id="csv-main"
              label="Primary dataset"
              file={file}
              onFile={setFile}
            />
            <FileDropzone
              id="csv-baseline"
              label="Baseline version"
              hint="Same schema, earlier snapshot"
              file={baseline}
              onFile={setBaseline}
              optional
            />

            <AnimatePresence>
              {error && (
                <motion.p
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                >
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            <Button
              size="lg"
              className="w-full"
              disabled={!file || loading}
              onClick={handleSubmit}
            >
              {loading ? (
                <Loader2 className="animate-spin" data-icon="inline-start" />
              ) : null}
              {loading ? "Analyzing…" : "Run quality analysis"}
            </Button>
          </CardContent>
        </Card>

        <div className="grid w-full gap-3 sm:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.06 }}
              className="rounded-xl border border-border/50 bg-card/50 px-3 py-3 text-left"
            >
              <p className="text-sm font-medium">{f.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {f.detail}
              </p>
            </motion.div>
          ))}
        </div>
      </FadeIn>
    </div>
  )
}
