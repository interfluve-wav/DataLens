"""
Load tabular datasets (CSV, Excel, ODS, JSON, Parquet) into a profiler-ready DataFrame.
"""

from hardening import enforce_dataframe_limits

import json
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import chardet
import numpy as np
import pandas as pd

_NA_TOKENS = frozenset({"", "NA", "N/A", "NULL", "null", "NaN", "nan", "None"})

EXCEL_EXTENSIONS = frozenset({".xlsx", ".xlsm", ".xls", ".ods"})

SUPPORTED_FORMATS: Dict[str, Dict[str, str]] = {
    ".csv": {"label": "CSV", "kind": "delimited"},
    ".tsv": {"label": "TSV", "kind": "delimited"},
    ".txt": {"label": "Delimited text", "kind": "delimited"},
    ".xlsx": {"label": "Excel", "kind": "excel"},
    ".xlsm": {"label": "Excel (macro)", "kind": "excel"},
    ".xls": {"label": "Excel 97–2003", "kind": "excel"},
    ".ods": {"label": "OpenDocument", "kind": "excel"},
    ".json": {"label": "JSON", "kind": "json"},
    ".parquet": {"label": "Parquet", "kind": "parquet"},
}


def list_supported_formats() -> List[Dict[str, Any]]:
    return [
        {"extension": ext, "label": meta["label"], "kind": meta["kind"]}
        for ext, meta in sorted(SUPPORTED_FORMATS.items())
    ]


def supported_extensions() -> Tuple[str, ...]:
    return tuple(SUPPORTED_FORMATS.keys())


def is_supported_filename(filename: str) -> bool:
    if not filename:
        return False
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in SUPPORTED_FORMATS)


def is_excel_filename(filename: str) -> bool:
    return file_extension(filename) in EXCEL_EXTENSIONS


def file_extension(filename: str) -> str:
    lower = filename.lower()
    for ext in sorted(SUPPORTED_FORMATS.keys(), key=len, reverse=True):
        if lower.endswith(ext):
            return ext
    return ""


def detect_encoding(file_bytes: bytes) -> str:
    result = chardet.detect(file_bytes)
    return result.get("encoding") or "utf-8"


def detect_delimiter(file_bytes_str: str, sample_size: int = 2048) -> str:
    sample = file_bytes_str[:sample_size]
    delimiters = [",", "\t", ";", "|"]
    counts = {d: sample.count(d) for d in delimiters}
    return max(counts, key=counts.get)


def _cell_to_profiler_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NA
    try:
        if pd.isna(value):
            return pd.NA
    except (TypeError, ValueError):
        pass
    if isinstance(value, (list, tuple, np.ndarray)):
        parts = [_cell_to_profiler_value(v) for v in value]
        parts = [p for p in parts if p is not pd.NA and p is not None]
        if not parts:
            return pd.NA
        return ", ".join(str(p) for p in parts)
    text = str(value).strip()
    if text in _NA_TOKENS:
        return pd.NA
    return text


def _dedupe_columns(columns: List[str]) -> List[str]:
    seen: Dict[str, int] = {}
    out: List[str] = []
    for col in columns:
        if col not in seen:
            seen[col] = 0
            out.append(col)
        else:
            seen[col] += 1
            out.append(f"{col}__{seen[col]}")
    return out


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()
    df.columns = _dedupe_columns([str(c).strip() for c in df.columns])

    keep_cols: List[str] = []
    for col in df.columns:
        if col.startswith("Unnamed:") and df[col].isna().all():
            continue
        keep_cols.append(col)
    df = df[keep_cols]

    for col in df.columns:
        df[col] = [_cell_to_profiler_value(v) for v in df[col].tolist()]
    return df.reset_index(drop=True)


def _load_delimited(file_bytes: bytes, delimiter: Optional[str] = None) -> pd.DataFrame:
    encoding = detect_encoding(file_bytes)
    head = file_bytes[:65536]
    try:
        text_sample = head.decode(encoding)
    except UnicodeDecodeError:
        encoding = "utf-8"
        text_sample = head.decode(encoding, errors="replace")
    sep = delimiter or detect_delimiter(text_sample)
    df = pd.read_csv(
        BytesIO(file_bytes),
        encoding=encoding,
        delimiter=sep,
        keep_default_na=True,
        na_values=list(_NA_TOKENS - {""}),
        dtype=str,
    )
    return normalize_dataframe(df)


def _excel_engine_read(
    buf: BytesIO, ext: str, sheet: Union[str, int]
) -> pd.DataFrame:
    errors: List[str] = []

    try:
        return pd.read_excel(buf, engine="calamine", sheet_name=sheet)
    except Exception as exc:
        errors.append(f"calamine: {exc}")
        buf.seek(0)

    if ext in (".xlsx", ".xlsm"):
        try:
            return pd.read_excel(buf, engine="openpyxl", sheet_name=sheet)
        except Exception as exc:
            errors.append(f"openpyxl: {exc}")
            buf.seek(0)

    if ext == ".xls":
        try:
            return pd.read_excel(buf, engine="xlrd", sheet_name=sheet)
        except Exception as exc:
            errors.append(f"xlrd: {exc}")
            buf.seek(0)

    if ext == ".ods":
        try:
            return pd.read_excel(buf, engine="odf", sheet_name=sheet)
        except Exception as exc:
            errors.append(f"odf: {exc}")

    raise ValueError("; ".join(errors) or f"Could not read {ext}")


def list_excel_sheets(file_bytes: bytes, filename: str) -> List[str]:
    ext = file_extension(filename)
    if ext not in EXCEL_EXTENSIONS:
        return []

    buf = BytesIO(file_bytes)
    try:
        book = pd.ExcelFile(buf, engine="calamine")
        return list(book.sheet_names)
    except Exception:
        buf.seek(0)

    if ext in (".xlsx", ".xlsm", ".xls"):
        try:
            book = pd.ExcelFile(buf, engine="openpyxl" if ext != ".xls" else "xlrd")
            return list(book.sheet_names)
        except Exception:
            buf.seek(0)

    if ext == ".ods":
        book = pd.ExcelFile(buf, engine="odf")
        return list(book.sheet_names)

    return []


def resolve_sheet_name(
    sheet_name: Optional[str], available: List[str]
) -> Union[str, int]:
    if not available:
        return 0
    if not sheet_name or not sheet_name.strip():
        return 0
    name = sheet_name.strip()
    if name.isdigit():
        idx = int(name)
        if 0 <= idx < len(available):
            return idx
        raise ValueError(
            f"Sheet index {idx} out of range (0–{len(available) - 1})"
        )
    if name in available:
        return name
    lower_map = {s.lower(): s for s in available}
    if name.lower() in lower_map:
        return lower_map[name.lower()]
    raise ValueError(
        f"Sheet '{name}' not found. Available: {', '.join(available)}"
    )


def _load_excel(
    file_bytes: bytes,
    ext: str,
    sheet_name: Optional[str] = None,
) -> pd.DataFrame:
    sheets = list_excel_sheets(file_bytes, f"file{ext}")
    sheet = resolve_sheet_name(sheet_name, sheets) if sheets else 0
    buf = BytesIO(file_bytes)
    df = _excel_engine_read(buf, ext, sheet)
    return normalize_dataframe(df)


def _load_json(file_bytes: bytes) -> pd.DataFrame:
    encoding = detect_encoding(file_bytes)
    try:
        text = file_bytes.decode(encoding)
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8", errors="replace")
    text = text.strip()
    if not text:
        raise ValueError("JSON file is empty")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if isinstance(payload, list):
        return normalize_dataframe(pd.json_normalize(payload))

    if isinstance(payload, dict):
        for key in ("data", "rows", "records", "items", "results"):
            if key in payload and isinstance(payload[key], list):
                return normalize_dataframe(pd.json_normalize(payload[key]))
        return normalize_dataframe(pd.json_normalize(payload))

    raise ValueError("JSON must be an array of objects or an object with row data")


def _load_parquet(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_parquet(BytesIO(file_bytes))
    return normalize_dataframe(df)


def load_tabular(
    file_bytes: bytes,
    filename: str = "data.csv",
    sheet_name: Optional[str] = None,
) -> pd.DataFrame:
    ext = file_extension(filename)
    if not ext:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ValueError(f"Unsupported file type. Supported: {supported}")

    if ext == ".tsv":
        df = _load_delimited(file_bytes, delimiter="\t")
    elif ext in (".csv", ".txt"):
        df = _load_delimited(file_bytes)
    elif ext in EXCEL_EXTENSIONS:
        df = _load_excel(file_bytes, ext, sheet_name)
    elif ext == ".json":
        df = _load_json(file_bytes)
    elif ext == ".parquet":
        df = _load_parquet(file_bytes)
    else:
        raise ValueError(f"Unsupported extension: {ext}")

    if df.empty or len(df.columns) == 0:
        raise ValueError("File has no rows or columns")

    enforce_dataframe_limits(df)
    return df


def load_csv(file_bytes: bytes) -> pd.DataFrame:
    return _load_delimited(file_bytes)
