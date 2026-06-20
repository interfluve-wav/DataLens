# DataLens — Tabular Data Quality Analyzer

**Score, diagnose, and fix tabular data before it hits your pipeline.** DataLens produces an auditable quality score (0–100), sector-specific data contracts, column-level diagnostics, interactive dashboards, one-click fixes, schema drift detection, and optional AI-assisted semantic review — all grounded in deterministic Python profiling.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](requirements.txt)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](api.py)
[![React](https://img.shields.io/badge/UI-React%20%2B%20Vite-61DAFB)](frontend/)

---

## About DataLens

DataLens is a **local-first data quality workbench** for analysts, researchers, and ML engineers who need a fast, repeatable answer to: *“Is this dataset trustworthy enough to use?”*

Profiling runs in Python first (`profiler.py` + `quality_profiles.py`). Every score, contract rule, and violation count comes from pandas/scipy on your machine. Optional **AI review** sends only a bounded summary of that output to a model (or uses the built-in mock verifier) — not your full dataset. The model cannot change scores or apply fixes.

### What you get

| Layer | What it does |
|-------|----------------|
| **Profiler** | Column stats, null/outlier/mixed-type detection, email/date/encoding checks |
| **Sector profiles** | Weighted dimension scores + pass/fail contracts for retail, healthcare, financial, survey, ML training |
| **Dashboards** | Overview, columns, distributions, BI analytics, fixes, drift, correlation, report |
| **Fixes** | Allowlisted transforms (`drop_nulls`, impute, strip whitespace, dedupe) with revision tracking |
| **AI review** | Triage of profiler evidence with confirmed issues, rejected false positives, and cited samples |

### Who it’s for

- **Survey / research teams** — duplicate respondents, item missingness, mixed-type Likert columns  
- **Retail / ops** — transaction keys, negative sales, duplicate rows  
- **ML practitioners** — label presence, feature completeness, correlation views  
- **Anyone with CSV/Excel/Parquet** — one upload, eight dashboards, exportable markdown report  

### Design principles

1. **Deterministic truth** — Python computes scores and rule pass/fail  
2. **Auditable** — revision history, sample failures, exportable reports  
3. **Local-first** — in-memory sessions for dev; no account required  
4. **Bounded AI** — capped sample rows and column summaries in review prompts  

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

Available on **Quality Overview → Run AI review** after upload.

**What happens today:**

1. A **context pack** is built from profiler output: failed rules, up to five sample rows per rule, and column summaries.  
2. A **verifier** returns structured JSON: `confirmed_issues`, `rejected_false_positives`, `evidence_refs`, and a short summary.  
3. Results are stored on the session and marked **stale** when you apply fixes or change the row sample (re-run to refresh).  
4. **Fixes** are still applied only through the Fixes dashboard — AI review does not auto-apply transforms.

**Providers (shipped):**

| `DATALENS_LLM_PROVIDER` | Behavior |
|-------------------------|----------|
| `mock` (default) | No API key; deterministic triage from profiler output |
| `openai` | Uses `OPENAI_API_KEY` and `DATALENS_LLM_MODEL` (default `gpt-4o-mini`) |
| `none` | Disables AI review UI and endpoints |

| Variable | Default | Description |
|----------|---------|-------------|
| `DATALENS_LLM_MAX_SAMPLE_ROWS` | `5` | Max sample rows per failed rule in the context pack |

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
│  llm_context.py → llm_verifier.py (optional advisory layer) │
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
| `POST /api/session/{id}/llm/verify` | Run AI semantic review |
| `GET /api/session/{id}/llm/verification` | Fetch stored verification + stale flag |
| `GET /api/llm/status` | Whether AI review is enabled and which provider is active |
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
├── llm_config.py          # LLM provider env
├── llm_context.py         # Context packer
├── llm_verifier.py        # Verifier (mock / OpenAI)
├── app.py                 # Legacy Streamlit UI
├── frontend/              # React primary UI
├── tests/                 # pytest suite
├── scripts/dev.sh         # Local dev orchestration
└── requirements.txt
```

---

## Validation

Scores and contract results trace to **pandas/scipy on real data**. AI review interprets that output; it does not replace profiling.

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
