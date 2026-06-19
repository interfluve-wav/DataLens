#!/usr/bin/env python3
"""Generate test fixtures in every supported tabular format."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)

RETAIL_ROWS = [
    {"store_id": "1", "date": "2024-06-01", "sku": "A", "sales": "100"},
    {"store_id": "2", "date": "2024-06-02", "sku": "B", "sales": "200"},
    {"store_id": "3", "date": "2024-06-03", "sku": "C", "sales": "150"},
    {"store_id": "4", "date": "", "sku": "D", "sales": "-5"},
]


def _df() -> pd.DataFrame:
    return pd.DataFrame(RETAIL_ROWS)


def write_delimited():
    df = _df()
    df.to_csv(FIXTURES / "retail_sample.csv", index=False)
    df.to_csv(FIXTURES / "retail_sample.tsv", sep="\t", index=False)
    df.to_csv(FIXTURES / "retail_sample.txt", sep="|", index=False)


def write_json():
    payload = {"records": RETAIL_ROWS}
    (FIXTURES / "retail_sample.json").write_text(json.dumps(payload, indent=2))


def write_parquet():
    df = _df()
    df.to_parquet(FIXTURES / "retail_sample.parquet", index=False)


def write_excel_multi():
    wb = Workbook()
    active = wb.active
    active.title = "Retail"
    active.append(["store_id", "date", "sku", "sales"])
    for row in RETAIL_ROWS:
        active.append([row["store_id"], row["date"], row["sku"], row["sales"]])

    archive = wb.create_sheet("Archive")
    archive.append(["store_id", "note"])
    archive.append(["99", "old"])

    wb.save(FIXTURES / "retail_sample.xlsx")
    wb.save(FIXTURES / "retail_sample.xlsm")


def write_ods():
    df = _df()
    try:
        df.to_excel(FIXTURES / "retail_sample.ods", index=False, engine="odf")
    except Exception as exc:
        print(f"WARN: ODS skipped ({exc})", file=sys.stderr)


def convert_downloaded_csv():
    src = FIXTURES / "sales_records_100.csv"
    if not src.exists():
        return
    df = pd.read_csv(src, nrows=50, dtype=str)
    df.to_parquet(FIXTURES / "sales_records_100.parquet", index=False)
    df.to_excel(FIXTURES / "sales_records_100.xlsx", index=False)
    with open(FIXTURES / "sales_records_100.json", "w") as f:
        json.dump(df.to_dict(orient="records"), f)


def main():
    write_delimited()
    write_json()
    write_parquet()
    write_excel_multi()
    write_ods()
    convert_downloaded_csv()
    print(f"Fixtures written to {FIXTURES}")
    for p in sorted(FIXTURES.glob("retail_sample.*")):
        print(f"  {p.name} ({p.stat().st_size} B)")
    for p in sorted(FIXTURES.glob("sales_records_100.*")):
        print(f"  {p.name} ({p.stat().st_size} B)")


if __name__ == "__main__":
    main()
