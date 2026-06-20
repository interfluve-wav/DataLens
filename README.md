# DataLens — Tabular Data Quality Analyzer

**Score, diagnose, and fix tabular data before it hits your pipeline.** DataLens produces an auditable quality score (0–100), sector-specific data contracts, column-level diagnostics, interactive dashboards, one-click fixes, and schema drift detection — all grounded in deterministic Python profiling.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](requirements.txt)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](api.py)
[![React](https://img.shields.io/badge/UI-React%20%2B%20Vite-61DAFB)](frontend/)

---

## About DataLens

DataLens is a **local-first data quality workbench** for analysts, researchers, and ML engineers who need a fast, repeatable answer to: *“Is this dataset trustworthy enough to use?”*

Profiling runs in Python (`profiler.py` + `quality_profiles.py`). Every score, contract rule, and violation count comes from pandas/scipy on your machine.

### What you get

| Layer | What it does |
|-------|----------------|
| **Profiler** | Column stats, null/outlier/mixed-type detection, email/date/encoding checks |
| **Sector profiles** | Weighted dimension scores + pass/fail contracts for retail, healthcare, financial, survey, ML training |
| **Dashboards** | Overview, columns, distributions, BI analytics, fixes, drift, correlation, report |
| **Fixes** | Allowlisted transforms (`drop_nulls`, impute, strip whitespace, dedupe) with revision tracking |

### Who it’s for

- **Survey / research teams** — duplicate respondents, item missingness, mixed-type Likert columns  
- **Retail / ops** — transaction keys, negative sales, duplicate rows  
- **ML practitioners** — label presence, feature completeness, correlation views  
- **Anyone with CSV/Excel/Parquet** — one upload, eight dashboards, exportable markdown report  

### Design principles

1. **Deterministic truth** — Python computes scores and rule pass/fail  
2. **Auditable** — revision history, sample failures, exportable reports  
3. **Local-first** — in-memory sessions for dev; no account required  
4. **Bounded sessions** — upload limits and row caps protect local memory use  

---

## Quickstart

### Recommended: React UI + FastAPI

```bash
git clone https://github.com/interfluve-wav/DataLens.git
cd DataLens

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# API (port 8000) + Vite frontend (port 5173)
./dev.sh
```

Open **http://localhost:5173** — upload a file, pick a sector profile, explore dashboards.

### Legacy: Streamlit

```bash
source venv/bin/activate
streamlit run app.py
# → http://localhost:8501
```

### Tests

```bash
venv/bin/python3 -m pytest tests/ -v
```

---

## Supported formats

CSV, TSV, Excel (`.xlsx`, `.xlsm`), ODS, JSON, Parquet — via `tabular_loader.py`.

---

## Quality profiles & contracts

| Profile | Focus |
|---------|--------|
| `generic` | Balanced hygiene scoring |
| `retail` | Store/date/SKU uniqueness, non-negative sales |
| `healthcare` | Clinical completeness, timeliness, precision |
| `financial` | Timeliness, email format (KYC-oriented) |
| `survey` | Respondent uniqueness, high per-row item missingness, required columns |
| `ml_training` | Label presence, duplicates, outliers |

Each profile produces **dimension scores** (weighted 0–100) and **contract rules** (critical vs warning) with `sample_failures` for failed checks.

---

## AI semantic review

Shown on **Quality Overview** as a preview card labeled **Coming in the next update**. The control is disabled in this release; deterministic profiling and fixes are fully available.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  frontend/ (React + Vite + shadcn + Recharts + GSAP)        │
│  Upload → 8 dashboards → fixes / report export              │
└───────────────────────────┬─────────────────────────────────┘
                            │ /api
┌───────────────────────────▼─────────────────────────────────┐
│  api.py (FastAPI, in-memory sessions, revision tracking)      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  profiler.py          tabular_loader.py    quality_profiles.py │
│  hardening.py (limits, VALID_FIX_TYPES, session TTL)          │
└─────────────────────────────────────────────────────────────┘
```

**Stack:** Python 3.12+, FastAPI, pandas, scipy, React 19, TypeScript, Vite  
**Legacy UI:** Streamlit (`app.py`) — kept for reference, not the primary surface  

---

## API highlights

| Endpoint | Purpose |
|----------|---------|
| `POST /api/upload` | Upload dataset + optional baseline + quality profile |
| `GET /api/session/{id}` | Full session payload (scores, rules, analytics) |
| `POST /api/fixes` | Apply allowlisted column fixes, bump revision |
| `GET /api/session/{id}/report` | Markdown quality report |

---

## Project structure

```
DataLens/
├── api.py                 # FastAPI backend
├── profiler.py            # Core profiling engine
├── quality_profiles.py    # Sector profiles + DQ contracts
├── tabular_loader.py      # Multi-format ingest
├── hardening.py           # Upload limits, sessions, fix allowlist
├── app.py                 # Legacy Streamlit UI
├── frontend/              # React primary UI
├── tests/                 # pytest suite
├── scripts/dev.sh         # Local dev orchestration
└── requirements.txt
```

---

## Validation

Scores and contract results trace to **pandas/scipy on real data**.

```bash
venv/bin/python3 -m pytest tests/ -v
```

---

## Contributing

1. Fork the repo  
2. Create a feature branch (`git checkout -b feature/your-feature`)  
3. Commit with a clear message  
4. Push and open a Pull Request  
5. Run `pytest` before submitting  

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Suhaas Chitturi** — [@interfluve-wav](https://github.com/interfluve-wav)
