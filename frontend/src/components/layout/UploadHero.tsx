import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import { Loader2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FadeIn } from "@/components/motion/GsapAnimations"
import { FileDropzone } from "@/components/layout/FileDropzone"
import { SheetPicker } from "@/components/layout/SheetPicker"
import { useDataLens } from "@/context/DataLensContext"
import { fetchQualityProfiles, inspectFile } from "@/lib/api"
import { isExcelFile, SUPPORTED_FORMATS_LABEL } from "@/lib/supportedFormats"
import type { QualityProfileId, QualityProfileInfo } from "@/types/datalens"

const FEATURES = [
  { title: "Multi-format", detail: "CSV, TSV, Excel, ODS, Parquet, JSON" },
  { title: "Sheet picker", detail: "Choose the right Excel or ODS tab" },
  { title: "8 dashboards", detail: "Columns, distributions, BI charts, drift & more" },
]

function useSheetInspection(file: File | null) {
  const [sheets, setSheets] = useState<string[]>([])
  const [sheetName, setSheetName] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!file || !isExcelFile(file.name)) {
      setSheets([])
      setSheetName("")
      return
    }
    let cancelled = false
    setLoading(true)
    inspectFile(file)
      .then((result) => {
        if (cancelled) return
        setSheets(result.sheets)
        setSheetName(result.sheets[0] ?? "")
      })
      .catch(() => {
        if (!cancelled) {
          setSheets([])
          setSheetName("")
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [file])

  return { sheets, sheetName, setSheetName, loading }
}

export function UploadHero() {
  const { upload, loading, error } = useDataLens()
  const [file, setFile] = useState<File | null>(null)
  const [baseline, setBaseline] = useState<File | null>(null)
  const [profiles, setProfiles] = useState<QualityProfileInfo[]>([])
  const [qualityProfile, setQualityProfile] = useState<QualityProfileId>("generic")
  const [requiredColumns, setRequiredColumns] = useState("")

  const mainSheets = useSheetInspection(file)
  const baselineSheets = useSheetInspection(baseline)

  useEffect(() => {
    fetchQualityProfiles()
      .then(setProfiles)
      .catch(() => setProfiles([]))
  }, [])

  const selectedProfile = profiles.find((p) => p.id === qualityProfile)

  const sharedOptions = {
    qualityProfile,
    requiredColumns,
  }

  const handleFileSubmit = async () => {
    if (!file) return
    await upload(file, baseline, {
      ...sharedOptions,
      sheetName: mainSheets.sheetName,
      baselineSheetName: baselineSheets.sheetName,
    })
  }

  const canSubmitFile = Boolean(file) && !loading

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
              Score, diagnose, and fix tabular data quality before it hits your pipeline.
            </p>
          </div>
        </div>

        <Card className="glass-panel w-full">
          <CardHeader>
            <CardTitle>Import dataset</CardTitle>
            <CardDescription>{SUPPORTED_FORMATS_LABEL}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor="quality-profile">Scoring profile</Label>
                <Select
                  value={qualityProfile}
                  onValueChange={(v) => setQualityProfile(v as QualityProfileId)}
                  disabled={loading}
                >
                  <SelectTrigger id="quality-profile" className="w-full">
                    <SelectValue placeholder="Select profile" />
                  </SelectTrigger>
                  <SelectContent>
                    {profiles.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.label}
                      </SelectItem>
                    ))}
                    {profiles.length === 0 && (
                      <SelectItem value="generic">Generic CSV</SelectItem>
                    )}
                  </SelectContent>
                </Select>
                {selectedProfile && (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {selectedProfile.description}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="required-cols">Required columns (optional)</Label>
                <Input
                  id="required-cols"
                  placeholder="store_id, date, sku"
                  value={requiredColumns}
                  onChange={(e) => setRequiredColumns(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated. Enables not-null contract rules on these fields.
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <FileDropzone
                id="csv-main"
                label="Primary dataset"
                file={file}
                onFile={setFile}
              />
              <SheetPicker
                id="main-sheet"
                label="Worksheet"
                sheets={mainSheets.sheets}
                value={mainSheets.sheetName}
                onChange={mainSheets.setSheetName}
                loading={mainSheets.loading}
              />
              <FileDropzone
                id="csv-baseline"
                label="Baseline version"
                hint="Same schema, earlier snapshot"
                file={baseline}
                onFile={setBaseline}
                optional
              />
              <SheetPicker
                id="baseline-sheet"
                label="Baseline worksheet"
                sheets={baselineSheets.sheets}
                value={baselineSheets.sheetName}
                onChange={baselineSheets.setSheetName}
                loading={baselineSheets.loading}
              />
              <Button
                size="lg"
                className="w-full"
                disabled={!canSubmitFile}
                onClick={handleFileSubmit}
              >
                {loading ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : null}
                {loading ? "Analyzing…" : "Run quality analysis"}
              </Button>
            </div>

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
