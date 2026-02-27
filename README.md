# Unstructured Text → Structured JSON Pipeline

> Convert raw text into validated, structured data using LLM agents

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Pydantic](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Pipeline Overview

```
 ┌─────────────────┐
 │  Raw Text Files │  (company descriptions, news, PDFs → .txt)
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐
 │  LLM Extraction │  Databricks · Llama 3.3 70B
 │  (structured    │  System prompt includes schema definition
 │   prompting)    │  Returns ONLY valid JSON
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐
 │ Pydantic v2     │  CompanyProfile / BuyerProfile
 │ Validation      │  Type coercion + custom validators
 │ + Confidence    │  0.0–1.0 confidence scoring
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐
 │ SQLite Storage  │  Lineage: source_file, extracted_at,
 │ (extractions.db)│  model_version, confidence_score
 └─────────────────┘
```

---

## Features

- 🤖 **LLM-powered extraction** — Llama 3.3 70B via Databricks Foundation Models (free tier)
- ✅ **Pydantic v2 validation** — strict typing, custom validators, clear error messages
- 📊 **Confidence scoring** — LLM self-reports extraction quality (0–1) per record
- 🔍 **Data lineage** — every row tracks source file, timestamp, and model version
- 🔁 **Retry logic** — automatic retries on API or parse failures with backoff

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/manuelarguelles/unstructured-to-json-llm-pipeline.git
cd unstructured-to-json-llm-pipeline

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env and add your DATABRICKS_TOKEN

# 4. Run the pipeline
python pipeline.py
```

---

## Example Output

```
════════════════════════════════════════════════════════════
  Unstructured → Structured JSON Pipeline
════════════════════════════════════════════════════════════

→ SQLite DB: extractions.db
→ Found 5 file(s) to process

→ Processing: acme_corp.txt  [CompanyProfile]
✔ Acme Corporation — confidence: 0.94

→ Processing: globex_industries.txt  [CompanyProfile]
✔ Globex Industries — confidence: 0.91

→ Processing: initech_capital.txt  [BuyerProfile]
✔ Initech Capital Partners — confidence: 0.88

→ Processing: oceanic_analytics.txt  [CompanyProfile]
✔ Oceanic Analytics — confidence: 0.95

→ Processing: wayne_enterprises.txt  [CompanyProfile]
✔ Wayne Enterprises — confidence: 0.90

────────────────────────────────────────────────────────────
  Summary
────────────────────────────────────────────────────────────
File                           Schema            Conf  Status
────────────────────────────────────────────────────────────
acme_corp.txt                  CompanyProfile    0.94  ✅ OK
globex_industries.txt          CompanyProfile    0.91  ✅ OK
initech_capital.txt            BuyerProfile      0.88  ✅ OK
oceanic_analytics.txt          CompanyProfile    0.95  ✅ OK
wayne_enterprises.txt          CompanyProfile    0.90  ✅ OK

Total: 5/5 successful extractions
```

**Extracted JSON example (acme_corp.txt → CompanyProfile):**

```json
{
  "company_name": "Acme Corporation",
  "industry": "Cloud Infrastructure / SaaS",
  "headquarters": "San Francisco, CA",
  "employee_count": 1200,
  "revenue_range": "$80M-$100M",
  "key_products": ["CloudSync", "DataBridge", "AutoScale"],
  "description": "Cloud infrastructure SaaS company focused on DevOps automation for mid-market enterprises.",
  "confidence_score": 0.94
}
```

---

## View Results

After running the pipeline, generate an interactive HTML report:

```bash
python view_results.py
```

This creates `output.html` and opens it in your browser — a visual dashboard showing all extractions with confidence scores, metadata, and raw JSON.

👉 **[View sample output](output.html)** — pre-generated from the 5 sample texts.

---

## Architecture

```
unstructured-to-json-llm-pipeline/
├── pipeline.py              # Main orchestrator (~180 lines)
├── models.py                # Pydantic v2 schemas
├── view_results.py          # HTML report generator
├── output.html              # Pre-generated results (viewable)
├── examples/
│   └── sample_texts/        # Input .txt files
│       ├── acme_corp.txt
│       ├── globex_industries.txt
│       ├── initech_capital.txt
│       ├── oceanic_analytics.txt
│       └── wayne_enterprises.txt
├── extractions.db           # Auto-created SQLite output (gitignored)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Key Design Decisions

| Decision | Why |
|----------|-----|
| Single `pipeline.py` | Readable, portfolio-friendly, no over-engineering |
| Pydantic v2 (not dataclasses) | Built-in JSON schema export for LLM prompts |
| SQLite (not Postgres) | Zero setup, runs anywhere, good enough for demo |
| httpx (not requests) | Async-ready, modern, clean timeout handling |
| Schema in system prompt | LLM stays focused; fewer hallucinations |

---

## Schemas

### CompanyProfile
| Field | Type | Description |
|-------|------|-------------|
| `company_name` | `str` | Legal or trade name |
| `industry` | `str` | Primary industry vertical |
| `headquarters` | `Optional[str]` | City, State / Country |
| `employee_count` | `Optional[int]` | Approximate headcount |
| `revenue_range` | `Optional[str]` | Annual revenue estimate |
| `key_products` | `list[str]` | Main products or services |
| `description` | `str` | 1-2 sentence summary |
| `confidence_score` | `float` | Extraction confidence (0–1) |

### BuyerProfile
| Field | Type | Description |
|-------|------|-------------|
| `company_name` | `str` | Firm name |
| `industry` | `str` | PE, VC, Corp Dev, etc. |
| `acquisition_interests` | `list[str]` | Target sectors / themes |
| `budget_range` | `Optional[str]` | Deal size or EBITDA range |
| `key_contacts` | `list[dict]` | Name, title, email |
| `deal_history` | `list[str]` | Recent transactions |
| `confidence_score` | `float` | Extraction confidence (0–1) |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built as a portfolio piece for Senior Data Engineer / AI Infrastructure roles.*
*Stack: Python · Pydantic v2 · Databricks Foundation Models · SQLite*
