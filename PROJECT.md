# unstructured-to-json-llm-pipeline

## Vision
Simple, clean demo: convert unstructured text into structured JSON using LLM agents with Pydantic validation and confidence scoring. Meant as a portfolio piece for a Senior Data Engineer + AI role.

## Stack
- Python 3.12+
- Pydantic v2 (schemas + validation)
- httpx (LLM API calls)
- SQLite (zero-setup storage)
- Databricks Foundation Models — Llama 3.3 70B (FREE, no cost)

## Constraints
- SIMPLE — one main file (~150-200 lines), not enterprise bloat
- Zero Docker, zero Airflow, zero PostgreSQL
- Must run with `python pipeline.py` and show results in 30 seconds
- Databricks API is the only external dependency (free tier)
- Public repo — NO secrets, NO API keys in code
- API key loaded from env var `DATABRICKS_TOKEN` or `.env` file

## Scope v1 (this)
- pipeline.py — main orchestrator (ingest → extract → validate → store)
- models.py — 2-3 Pydantic schemas (CompanyProfile, BuyerProfile)
- examples/sample_texts/ — 5-10 raw text files (company descriptions, news)
- README.md — clear explanation, diagram, quickstart, example output
- .env.example — template for API config
- requirements.txt — minimal deps

## Scope v2 (deferred)
- Notebook demo
- Multiple LLM providers
- Human-in-the-loop review queue
- Batch processing
- REST API wrapper

## LLM API Details
- Endpoint: https://dbc-5c46f062-96ed.cloud.databricks.com/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations
- Auth: Bearer token (env var DATABRICKS_TOKEN)
- Format: OpenAI-compatible chat completions
- Model: databricks-meta-llama-3-3-70b-instruct
- FREE — no cost, no rate limit issues for demo

## Key Features to Demonstrate
1. LLM-powered extraction with structured prompts (system + user)
2. Pydantic validation with custom validators
3. Confidence scoring (LLM assigns 0-1 score per extraction)
4. Data lineage (source, timestamp, model version tracked per record)
5. Error handling (retries, graceful failures, partial extraction)
6. Clean, typed, documented Python code

## Links
- Repo: github.com/manuelarguelles/unstructured-to-json-llm-pipeline
- Related job application: Common Forge Ventures — Sr Data Engineer AI Infrastructure
