import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { uploadCsv, applyFixes as apiApplyFixes, setRowSample as apiSetRowSample } from "@/lib/api"
import type { DashboardId, UploadResponse } from "@/types/datalens"

interface DataLensContextValue {
  data: UploadResponse | null
  loading: boolean
  error: string | null
  activeDashboard: DashboardId
  setActiveDashboard: (id: DashboardId) => void
  upload: (file: File, baseline?: File | null) => Promise<void>
  applyFixes: (fixes: Record<string, string>) => Promise<void>
  setRowSample: (rowLimit: number | null) => Promise<void>
  clear: () => void
}

const DataLensContext = createContext<DataLensContextValue | null>(null)

export function DataLensProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<UploadResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeDashboard, setActiveDashboard] =
    useState<DashboardId>("overview")

  const upload = useCallback(async (file: File, baseline?: File | null) => {
    setLoading(true)
    setError(null)
    try {
      const result = await uploadCsv(file, baseline)
      setData(result)
      setActiveDashboard("overview")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed")
    } finally {
      setLoading(false)
    }
  }, [])

  const applyFixes = useCallback(
    async (fixes: Record<string, string>) => {
      if (!data) return
      setLoading(true)
      setError(null)
      try {
        const result = await apiApplyFixes(data.session_id, fixes)
        setData(result)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to apply fixes")
      } finally {
        setLoading(false)
      }
    },
    [data],
  )

  const setRowSample = useCallback(
    async (rowLimit: number | null) => {
      if (!data) return
      setLoading(true)
      setError(null)
      try {
        const result = await apiSetRowSample(data.session_id, rowLimit)
        setData(result)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to update sample")
        throw e
      } finally {
        setLoading(false)
      }
    },
    [data],
  )

  const clear = useCallback(() => {
    setData(null)
    setError(null)
    setActiveDashboard("overview")
  }, [])

  const value = useMemo(
    () => ({
      data,
      loading,
      error,
      activeDashboard,
      setActiveDashboard,
      upload,
      applyFixes,
      setRowSample,
      clear,
    }),
    [
      data,
      loading,
      error,
      activeDashboard,
      upload,
      applyFixes,
      setRowSample,
      clear,
    ],
  )

  return (
    <DataLensContext.Provider value={value}>{children}</DataLensContext.Provider>
  )
}

export function useDataLens() {
  const ctx = useContext(DataLensContext)
  if (!ctx) throw new Error("useDataLens must be used within DataLensProvider")
  return ctx
}
