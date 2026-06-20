import { Loader2, Rows3 } from "lucide-react"
import { toast } from "sonner"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { useDataLens } from "@/context/DataLensContext"
import { ROW_SAMPLE_PRESETS } from "@/types/datalens"

function formatRows(n: number) {
  return n.toLocaleString()
}

export function RowSampleSelect() {
  const { data, loading, setRowSample } = useDataLens()
  if (!data) return null

  const total = data.total_row_count ?? data.row_count
  const currentValue =
    data.row_sample_limit != null ? String(data.row_sample_limit) : "all"

  const presets = ROW_SAMPLE_PRESETS.filter((n) => n < total)

  const handleChange = async (value: string) => {
    const limit = value === "all" ? null : parseInt(value, 10)
    try {
      await setRowSample(limit)
      if (limit === null) {
        toast.success(`Analyzing all ${formatRows(total)} rows`)
      } else {
        toast.success(`Sampled ${formatRows(limit)} of ${formatRows(total)} rows`)
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Sample failed")
    }
  }

  return (
    <div className="flex items-center gap-2">
      {loading && (
        <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
      )}
      <Label htmlFor="row-sample" className="sr-only">
        Row sample
      </Label>
      <Select value={currentValue} onValueChange={handleChange} disabled={loading}>
        <SelectTrigger id="row-sample" size="sm" className="w-[9.5rem] gap-1.5">
          <Rows3 className="size-3.5 shrink-0 text-muted-foreground" />
          <SelectValue placeholder="Rows" />
        </SelectTrigger>
        <SelectContent className="max-h-72">
          <SelectGroup>
            <SelectItem value="all">
              All rows ({formatRows(total)})
            </SelectItem>
            {presets.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {formatRows(n)} rows
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      {data.is_sampled && (
        <Badge variant="secondary" className="hidden sm:inline-flex text-xs">
          {formatRows(data.row_count)} sampled
        </Badge>
      )}
    </div>
  )
}
