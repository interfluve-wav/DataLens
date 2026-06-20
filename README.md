# DataLens — Tabular Data Quality Analyzer

**Score, diagnose, and fix tabular data before it hits your pipeline.** DataLens produces an auditable quality score (0–100), sector-specific data contracts, column-level diagnostics, interactive dashboards, one-click fixes, schema drift detection, and optional AI-assisted semantic review — all grounded in deterministic Python profiling.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](requirements.txt)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](api.py)
[![React](https://img.shields.io/badge/UI-React%20%2B%20Vite-61DAFB)](frontend/)

---

## About DataLens

DataLens is a **local-first data quality workbench** for analysts, researchers, and ML engineers who need a fast, repeatable answer to: *“Is this dataset trustworthy enough to use?”*

Unlike chat-only AI tools, DataLens runs **deterministic profiling first** (`profiler.py` + `quality_profiles.py`). Every score, contract rule, and violation count comes from pandas/scipy on your machine. Optional LLM review (Phase 1) only interprets a **bounded summary** of that output — it never sees your full dataset and cannot change scores or apply fixes without your approval.

### What you get

| Layer | What it does |
|-------|----------------|
| **Profiler** | Column stats, null/outlier/mixed-type detection, email/date/encoding checks |
| **Sector profiles** | Weighted dimension scores + pass/fail contracts for retail, healthcare, financial, survey, ML training |
| **Dashboards** | Overview, columns, distributions, BI analytics, fixes, drift, correlation, report |
| **Fixes** | Allowlisted transforms (`drop_nulls`, impute, strip whitespace, dedupe) with revision tracking |
| **AI review** | Semantic triage over profiler evidence (mock or OpenAI); sub-cent per review on budget models |

### Who it’s for

- **Survey / research teams** — duplicate respondents, item missingness, Likert encoding issues  
- **Retail / ops** — transaction keys, negative sales, duplicate rows  
- **ML practitioners** — label presence, feature completeness, leakage hints via correlation  
- **Anyone with CSV/Excel/Parquet** — one upload, eight dashboards, exportable markdown report  

### Design principles

1. **Deterministic truth** — Python counts; LLM advises  
2. **Auditable** — revision history, sample failures, exportable reports  
3. **Polish over enterprise** — in-memory sessions, no auth wall for local dev  
4. **Bounded AI** — context packer caps tokens; no raw PII in prompts by default  

See [docs/DataLens-LLM-Integration-Architecture-Proposal.md](docs/DataLens-LLM-Integration-Architecture-Proposal.md) for the full LLM roadmap (verifier → fix planner → executor).

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
| `survey` | Respondent uniqueness, item missingness, completeness |
| `ml_training` | Label presence, duplicates, outliers |

Each profile produces **dimension scores** (weighted 0–100) and **contract rules** (critical vs warning) with `sample_failures` for failed checks.

---

## AI semantic review (Phase 1)

After upload, open **Quality Overview → Run AI review**. The pipeline:

1. **Context packer** — failed rules, capped sample rows, column summaries (~1.5–2.5k input tokens)  
2. **Verifier** — structured JSON: confirmed issues, rejected false positives, evidence refs  
3. **You** — read results; fixes still require explicit approval (Phase 2 planner coming)

### LLM configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATALENS_LLM_PROVIDER` | `mock` | `mock` \| `openai` \| `none` |
| `DATALENS_LLM_MODEL` | `gpt-4o-mini` | OpenAI model when provider is `openai` |
| `OPENAI_API_KEY` | — | Required for `openai` provider |
| `DATALENS_LLM_MAX_SAMPLE_ROWS` | `5` | Max sample rows per failed rule in context pack |

`mock` runs without an API key (deterministic triage from profiler output). Set `none` to hide AI UI.

**Cost ballpark** (one review, ~2.5k in / 1.5k out): Fireworks DeepSeek V4 Flash **&lt;0.1¢**, DeepSeek V4 Pro **~1¢**, Claude Opus 4.7 / GPT-5.5 **~5–6¢** — independent of dataset row count.

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
├── llm_context.py         # Context packer (bounded prompt payload)
├── llm_verifier.py        # Verifier (mock / OpenAI)
├── app.py                 # Legacy Streamlit UI
├── frontend/              # React primary UI
├── tests/                 # pytest suite
├── docs/                  # Architecture & design docs
├── scripts/dev.sh         # Local dev orchestration
└── requirements.txt
```

---

## Validation

Scores and contract results trace to **pandas/scipy on real data** — not LLM guesses.

```bash
venv/bin/python3 -m pytest tests/ -v
```

Integration tests cover multi-format upload, retail/survey contracts, API hardening, analytics, and LLM verify + revision invalidation.

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

DataLens demonstrates production-minded data quality tooling: deterministic analytics, sector contracts, a modern React dashboard, and a trust-boundary-aware LLM integration path.
