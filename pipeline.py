"""
pipeline.py — Unstructured Text → Structured JSON Pipeline
Orchestrates: ingest → LLM extraction → Pydantic validation → SQLite storage

Usage:
    python pipeline.py
"""

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from models import BuyerProfile, CompanyProfile, infer_schema

# ── Constants ──────────────────────────────────────────────────────────────────
DATABRICKS_ENDPOINT = (
    "https://dbc-5c46f062-96ed.cloud.databricks.com"
    "/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations"
)
MODEL_VERSION = "databricks-meta-llama-3-3-70b-instruct"
DB_PATH = "extractions.db"
SAMPLE_DIR = Path("examples/sample_texts")
MAX_RETRIES = 2

# ── Colors ─────────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}✔ {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠ {msg}{RESET}")


def err(msg: str) -> None:
    print(f"{RED}✖ {msg}{RESET}")


def info(msg: str) -> None:
    print(f"{CYAN}→ {msg}{RESET}")


# ── Config ─────────────────────────────────────────────────────────────────────
def load_config() -> dict[str, str]:
    """Load configuration from environment or .env file."""
    load_dotenv()
    token = os.getenv("DATABRICKS_TOKEN")
    if not token:
        raise EnvironmentError(
            "DATABRICKS_TOKEN not found. Set it in .env or as an environment variable.\n"
            "See .env.example for reference."
        )
    return {"token": token}


# ── LLM Extraction ─────────────────────────────────────────────────────────────
def build_system_prompt(schema_class: type) -> str:
    """Build a system prompt with explicit field list (not raw JSON schema)."""
    # Build a simple field description instead of the raw JSON schema
    # This prevents the LLM from returning the schema itself as data
    fields = schema_class.model_fields
    field_lines = []
    for name, field_info in fields.items():
        annotation = str(field_info.annotation).replace("typing.", "")
        required = "required" if field_info.is_required() else "optional, use null if unknown"
        field_lines.append(f'  - "{name}": {annotation} ({required})')
    fields_str = "\n".join(field_lines)

    return (
        "You are a precise data extraction assistant. "
        "Read unstructured text and extract structured information.\n\n"
        "Return ONLY a valid JSON object with these fields:\n"
        f"{fields_str}\n\n"
        "RULES:\n"
        "1. Return ONLY the JSON object — no markdown, no code fences, no explanations, no schema.\n"
        "2. Fill every field with actual extracted data from the text.\n"
        "3. For fields you cannot determine, use null (for optional) or [] (for lists).\n"
        "4. confidence_score: float 0.0-1.0 based on extraction certainty.\n"
        "5. key_products / key_contacts / deal_history: extract as lists from the text.\n"
        "6. Do NOT return the schema definition — return the EXTRACTED DATA.\n"
        "7. Do NOT invent or hallucinate data."
    )


def extract_json_from_text(raw: str) -> dict[str, Any]:
    """Extract JSON object from LLM response, handling occasional markdown fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    # Find the first JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw[:200]!r}")
    return json.loads(match.group())


def extract_to_json(
    raw_text: str,
    schema_class: type[CompanyProfile] | type[BuyerProfile],
    token: str,
) -> CompanyProfile | BuyerProfile:
    """
    Call Databricks Llama 3.3 70B to extract structured data from raw text.
    Returns a validated Pydantic model instance.
    Retries up to MAX_RETRIES times on API or parse failure.
    """
    system_prompt = build_system_prompt(schema_class)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract structured data from this text:\n\n{raw_text}"},
        ],
        "max_tokens": 2000,
    }

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 2):  # 1 initial + MAX_RETRIES retries
        try:
            if attempt > 1:
                wait = attempt * 2
                warn(f"  Retry {attempt - 1}/{MAX_RETRIES} after {wait}s...")
                time.sleep(wait)

            with httpx.Client(timeout=60.0) as client:
                response = client.post(DATABRICKS_ENDPOINT, headers=headers, json=body)
                response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            extracted = extract_json_from_text(content)
            return schema_class(**extracted)

        except httpx.HTTPStatusError as exc:
            last_exc = exc
            err(f"  HTTP {exc.response.status_code}: {exc.response.text[:200]}")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            last_exc = exc
            err(f"  Parse error: {exc}")

    raise RuntimeError(
        f"Failed after {MAX_RETRIES + 1} attempts. Last error: {last_exc}"
    )


# ── Storage ────────────────────────────────────────────────────────────────────
def init_db(db_path: str) -> None:
    """Create SQLite tables if they don't exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file    TEXT    NOT NULL,
                schema_type    TEXT    NOT NULL,
                company_name   TEXT,
                industry       TEXT,
                extracted_json TEXT    NOT NULL,
                confidence_score REAL,
                model_version  TEXT    NOT NULL,
                extracted_at   TEXT    NOT NULL
            )
        """)
        conn.commit()


def store_result(
    profile: CompanyProfile | BuyerProfile,
    source_file: str,
    db_path: str = DB_PATH,
) -> None:
    """Insert an extraction result with full lineage into SQLite."""
    schema_type = type(profile).__name__
    extracted_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO extractions
                (source_file, schema_type, company_name, industry,
                 extracted_json, confidence_score, model_version, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_file,
                schema_type,
                profile.company_name,
                profile.industry,
                profile.model_dump_json(),
                profile.confidence_score,
                MODEL_VERSION,
                extracted_at,
            ),
        )
        conn.commit()


# ── Per-file Processing ────────────────────────────────────────────────────────
def process_file(
    filepath: Path,
    schema_class: type[CompanyProfile] | type[BuyerProfile],
    token: str,
    db_path: str = DB_PATH,
) -> dict[str, Any]:
    """Read → extract → validate → store one file. Returns a result summary dict."""
    info(f"Processing: {filepath.name}  [{schema_class.__name__}]")
    raw_text = filepath.read_text(encoding="utf-8")

    try:
        profile = extract_to_json(raw_text, schema_class, token)
        store_result(profile, str(filepath), db_path)
        ok(f"  {profile.company_name} — confidence: {profile.confidence_score:.2f}")
        return {
            "file": filepath.name,
            "company": profile.company_name,
            "schema": schema_class.__name__,
            "confidence": profile.confidence_score,
            "status": "✅ OK",
        }
    except Exception as exc:
        err(f"  Failed: {exc}")
        return {
            "file": filepath.name,
            "company": "—",
            "schema": schema_class.__name__,
            "confidence": 0.0,
            "status": f"❌ {type(exc).__name__}",
        }


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}  Unstructured → Structured JSON Pipeline{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}\n")

    # Load config
    try:
        config = load_config()
    except EnvironmentError as exc:
        err(str(exc))
        raise SystemExit(1)

    # Init DB
    init_db(DB_PATH)
    info(f"SQLite DB: {DB_PATH}")

    # Discover files
    txt_files = sorted(SAMPLE_DIR.glob("*.txt"))
    if not txt_files:
        warn(f"No .txt files found in {SAMPLE_DIR}")
        raise SystemExit(0)

    info(f"Found {len(txt_files)} file(s) to process\n")

    # Process each file
    results = []
    for filepath in txt_files:
        schema_class = infer_schema(filepath.name)
        result = process_file(filepath, schema_class, config["token"])
        results.append(result)
        print()

    # Summary table
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}  Summary{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")
    header = f"{'File':<30} {'Schema':<16} {'Conf':>5}  {'Status'}"
    print(f"{BOLD}{header}{RESET}")
    print("─" * 60)
    for r in results:
        conf_str = f"{r['confidence']:.2f}"
        row = f"{r['file']:<30} {r['schema']:<16} {conf_str:>5}  {r['status']}"
        color = GREEN if "OK" in r["status"] else RED
        print(f"{color}{row}{RESET}")

    success = sum(1 for r in results if "OK" in r["status"])
    print(f"\n{BOLD}Total: {success}/{len(results)} successful extractions{RESET}\n")


if __name__ == "__main__":
    main()
