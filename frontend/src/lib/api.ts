import type {
  ColumnDataResponse,
  UploadResponse,
} from "@/types/datalens"

const API_BASE = import.meta.env.VITE_API_URL ?? ""

export async function uploadCsv(
  file: File,
  baseline?: File | null,
): Promise<UploadResponse> {
  const form = new FormData()
  form.append("file", file)
  if (baseline) {
    form.append("baseline", baseline)
  }

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: form,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "Upload failed")
  }

  return res.json()
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
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "Failed to apply fixes")
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
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "Failed to update row sample")
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
