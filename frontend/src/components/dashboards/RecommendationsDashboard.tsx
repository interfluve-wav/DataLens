import { useState } from "react"
import { motion } from "motion/react"
import { Wrench } from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DashboardHeader } from "@/components/layout/DashboardHeader"
import { useDataLens } from "@/context/DataLensContext"
import type { ColumnProfile, UploadResponse } from "@/types/datalens"

function getFixOptions(profile: ColumnProfile) {
  const options: { key: string; label: string }[] = []

  if (profile.null_pct > 50) {
    options.push({ key: "drop_nulls", label: "Drop rows with null values" })
  } else if (profile.null_pct > 0) {
    if (profile.dtype === "numeric") {
      options.push({ key: "impute_median", label: "Impute nulls with median" })
    } else {
      options.push({ key: "impute_mode", label: "Impute nulls with mode" })
    }
  }

  if ((profile.whitespace_count ?? 0) > 0) {
    options.push({ key: "strip_whitespace", label: "Strip whitespace" })
  }

  return options
}

export function RecommendationsDashboard({ data }: { data: UploadResponse }) {
  const { applyFixes, loading } = useDataLens()
  const [pending, setPending] = useState<Record<string, string>>({})

  const allRecs = data.profiles.flatMap((p) =>
    p.recommendations.map((rec) => ({ profile: p, rec })),
  )

  const handleApply = async () => {
    if (Object.keys(pending).length === 0) {
      toast.error("Select at least one fix")
      return
    }
    await applyFixes(pending)
    setPending({})
    toast.success("Fixes applied — data re-profiled")
  }

  if (allRecs.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <DashboardHeader
          title="Fixes & Recommendations"
          description="Actionable transforms based on detected issues."
          data={data}
        />
        <Card className="glass-panel border-primary/20">
          <CardHeader>
            <CardTitle>All clear</CardTitle>
            <CardDescription>
              No issues detected — your data looks clean.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <DashboardHeader
        title="Fixes & Recommendations"
        description="Pick transforms per column, then apply in one batch."
        data={data}
        actions={
          <Button
            onClick={handleApply}
            disabled={loading || Object.keys(pending).length === 0}
          >
            <Wrench data-icon="inline-start" />
            Apply {Object.keys(pending).length || ""} fix
            {Object.keys(pending).length === 1 ? "" : "es"}
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        {allRecs.map(({ profile, rec }, i) => {
          const fixOptions = getFixOptions(profile)
          return (
            <motion.div
              key={`${profile.name}-${i}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <Card className="glass-panel h-full">
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-base">{profile.name}</CardTitle>
                    <Badge variant="outline">{profile.dtype}</Badge>
                  </div>
                  <CardDescription>{rec}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  {profile.issues.map((issue) => (
                    <p key={issue} className="text-sm text-muted-foreground">
                      • {issue}
                    </p>
                  ))}
                </CardContent>
                {fixOptions.length > 0 && (
                  <CardFooter>
                    <Select
                      value={pending[profile.name] ?? ""}
                      onValueChange={(v: string) =>
                        setPending((prev) => ({ ...prev, [profile.name]: v }))
                      }
                      disabled={loading}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Choose a fix…" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {fixOptions.map((f) => (
                            <SelectItem key={f.key} value={f.key}>
                              {f.label}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </CardFooter>
                )}
              </Card>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
