export const SUPPORTED_FILE_EXTENSIONS = [
  ".csv",
  ".tsv",
  ".txt",
  ".xlsx",
  ".xlsm",
  ".xls",
  ".ods",
  ".json",
  ".parquet",
] as const

export const EXCEL_FILE_EXTENSIONS = [".xlsx", ".xlsm", ".xls", ".ods"] as const

export const ACCEPT_FILE_TYPES = SUPPORTED_FILE_EXTENSIONS.join(",")

export function isSupportedFile(name: string): boolean {
  const lower = name.toLowerCase()
  return SUPPORTED_FILE_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

export function isExcelFile(name: string): boolean {
  const lower = name.toLowerCase()
  return EXCEL_FILE_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

export const SUPPORTED_FORMATS_LABEL =
  "CSV, TSV, Excel, ODS, JSON, or Parquet"
