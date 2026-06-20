import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function SheetPicker({
  id,
  label,
  sheets,
  value,
  onChange,
  loading,
}: {
  id: string
  label: string
  sheets: string[]
  value: string
  onChange: (sheet: string) => void
  loading?: boolean
}) {
  if (sheets.length <= 1) return null

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Select value={value} onValueChange={onChange} disabled={loading}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder={loading ? "Loading sheets…" : "Select sheet"} />
        </SelectTrigger>
        <SelectContent className="max-h-72">
          {sheets.map((sheet) => (
            <SelectItem key={sheet} value={sheet}>
              {sheet}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
