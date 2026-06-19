import type {
  ColumnDataResponse,
  InspectResponse,
  QualityProfileId,
  QualityProfileInfo,
  UploadResponse,
} from "@/types/datalens"

const API_BASE = import.meta.env.VITE_API_URL ?? ""

export type UploadOptions = {
  qualityProfile?: QualityProfileId
  requiredColumns?: string
  sheetName?: string
  baselineSheetName?: string
}

type ValidationErrorItem = {
  msg?: string
  loc?: unknown[]
}

export function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item
        if (item && typeof item === "object" && "msg" in item) {
          const err = item as ValidationErrorItem
          const loc = Array.isArray(err.loc)
            ? err.loc.filter((part) => part !== "body").join(".")
            : ""
          return loc && err.msg ? `${loc}: ${err.msg}` : String(err.msg ?? item)
        }
        return JSON.stringify(item)
      })
      .filter(Boolean)
    if (parts.length > 0) return parts.join("; ")
  }
  if (detail && typeof detail === "object") {
    if ("message" in detail && detail.message != null) {
      return String(detail.message)
    }
    if ("detail" in detail && detail.detail != null) {
      return formatApiError(detail.detail, fallback)
    }
  }
  if (detail != null) return String(detail)
  return fallback
}

async function readApiError(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => ({ detail: res.statusText }))
  return formatApiError(err.detail ?? err.message ?? err, fallback)
}

let profilesCache: QualityProfileInfo[] | null = null
let profilesPromise: Promise<QualityProfileInfo[]> | null = null

export function fetchQualityProfiles(): Promise<QualityProfileInfo[]> {
  if (profilesCache) return Promise.resolve(profilesCache)
  if (profilesPromise) return profilesPromise

  profilesPromise = (async () => {
    const res = await fetch(`${API_BASE}/api/profiles`)
    if (!res.ok) throw new Error("Failed to load quality profiles")
    const body = await res.json()
    profilesCache = body.profiles as QualityProfileInfo[]
    return profilesCache
  })()

  return profilesPromise
}

export async function inspectFile(file: File): Promise<InspectResponse> {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${API_BASE}/api/inspect`, { method: "POST", body: form })
  if (!res.ok) {
    throw new Error(await readApiError(res, "Failed to inspect file"))
  }
  return res.json()
}

function appendUploadOptions(form: FormData, options?: UploadOptions) {
  if (options?.qualityProfile) {
    form.append("quality_profile", options.qualityProfile)
  }
  if (options?.requiredColumns?.trim()) {
    form.append("required_columns", options.requiredColumns.trim())
  }
  if (options?.sheetName?.trim()) {
    form.append("sheet_name", options.sheetName.trim())
  }
  if (options?.baselineSheetName?.trim()) {
    form.append("baseline_sheet_name", options.baselineSheetName.trim())
  }
}

export async function uploadDataset(
  file: File,
  baseline?: File | null,
  options?: UploadOptions,
): Promise<UploadResponse> {
  const form = new FormData()
  form.append("file", file)
  if (baseline) {
    form.append("baseline", baseline)
  }
  appendUploadOptions(form, options)

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: form,
  })

  if (!res.ok) {
    throw new Error(await readApiError(res, "Upload failed"))
  }

  return res.json()
}

/** @deprecated use uploadDataset */
export const uploadCsv = uploadDataset

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/api/session/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  })
}

export async function getSession(sessionId: string): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}`)
  if (!res.ok) throw new Error("Session not found")
  return res.json()
}

export async function getColumnData(
  sessionId: string,
  column: string,
): Promise<ColumnDataResponse> {
  const res = await fetch(
    `${API_BASE}/api/session/${sessionId}/column/${encodeURIComponent(column)}`,
  )
  if (!res.ok) throw new Error("Failed to load column data")
  return res.json()
}

export async function applyFixes(
  sessionId: string,
  fixes: Record<string, string>,
): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/fixes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, fixes }),
  })
  if (!res.ok) {
    throw new Error(await readApiError(res, "Failed to apply fixes"))
  }
  return res.json()
}

export async function setRowSample(
  sessionId: string,
  rowLimit: number | null,
): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/api/sample`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, row_limit: rowLimit }),
  })
  if (!res.ok) {
    throw new Error(await readApiError(res, "Failed to update row sample"))
  }
  return res.json()
}

export async function getReport(
  sessionId: string,
): Promise<{ markdown: string; filename: string }> {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/report`)
  if (!res.ok) throw new Error("Failed to generate report")
  return res.json()
}
