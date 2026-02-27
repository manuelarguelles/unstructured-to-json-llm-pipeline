"""
view_results.py — Generate an HTML report from the extractions database.

Usage:
    python view_results.py          # generates output.html and opens it
    python view_results.py --no-open  # generates without opening
"""

import html
import json
import sqlite3
import sys
import subprocess
import platform
from pathlib import Path

DB_PATH = "extractions.db"
OUTPUT = "output.html"


def generate_html(db_path: str = DB_PATH) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM extractions ORDER BY id").fetchall()
    conn.close()

    if not rows:
        return "<html><body><h1>No extractions yet. Run: python pipeline.py</h1></body></html>"

    cards = ""
    for r in rows:
        data = json.loads(r["extracted_json"])
        fname = r["source_file"].split("/")[-1]
        conf = r["confidence_score"]
        conf_color = "#00ff88" if conf >= 0.9 else "#ffaa00" if conf >= 0.7 else "#ff4444"

        # Build detail rows
        details = ""
        if r["schema_type"] == "CompanyProfile":
            details = f"""
            <div class="field"><span class="label">Headquarters</span>{data.get('headquarters', 'N/A')}</div>
            <div class="field"><span class="label">Employees</span>{data.get('employee_count', 'N/A'):,}</div>
            <div class="field"><span class="label">Revenue</span>{data.get('revenue_range', 'N/A')}</div>
            <div class="field"><span class="label">Products</span>{', '.join(data.get('key_products', []))}</div>
            """
        else:
            contacts = ", ".join(f"{c.get('name','?')} ({c.get('title','?')})" for c in data.get("key_contacts", []))
            deals = "<br>".join(data.get("deal_history", []))
            interests = ", ".join(data.get("acquisition_interests", []))
            details = f"""
            <div class="field"><span class="label">Budget</span>{data.get('budget_range', 'N/A')}</div>
            <div class="field"><span class="label">Interests</span>{interests}</div>
            <div class="field"><span class="label">Contacts</span>{contacts}</div>
            <div class="field"><span class="label">Deals</span>{deals}</div>
            """

        pretty_json = html.escape(json.dumps(data, indent=2, ensure_ascii=False))

        cards += f"""
        <div class="card">
            <div class="card-header">
                <div>
                    <h2>{data.get('company_name', 'Unknown')}</h2>
                    <span class="tag">{data.get('industry', 'N/A')}</span>
                    <span class="tag schema">{r['schema_type']}</span>
                </div>
                <div class="confidence" style="border-color: {conf_color}; color: {conf_color}">
                    {conf:.0%}
                </div>
            </div>
            <div class="card-body">
                <div class="meta">
                    <span>📄 {fname}</span>
                    <span>🤖 {r['model_version']}</span>
                    <span>🕐 {r['extracted_at'][:19]}</span>
                </div>
                {details}
                <details>
                    <summary>View raw JSON</summary>
                    <pre>{pretty_json}</pre>
                </details>
            </div>
        </div>
        """

    success = len(rows)
    avg_conf = sum(r["confidence_score"] for r in rows) / len(rows)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Extraction Results — Unstructured → JSON Pipeline</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
        background: #0f0f1a; color: #e0e0e0; padding: 24px; }}
.container {{ max-width: 900px; margin: 0 auto; }}
h1 {{ color: #00d2ff; font-size: 28px; margin-bottom: 4px; }}
.subtitle {{ color: #888; margin-bottom: 24px; }}
.stats {{ display: flex; gap: 16px; margin-bottom: 24px; }}
.stat {{ background: #1a1a2e; border-radius: 10px; padding: 16px 20px; flex: 1; text-align: center; }}
.stat-value {{ font-size: 28px; font-weight: bold; color: #00ff88; }}
.stat-label {{ font-size: 12px; color: #888; margin-top: 4px; }}
.card {{ background: #1a1a2e; border-radius: 12px; margin-bottom: 16px; overflow: hidden; 
         border: 1px solid #2a2a4a; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; 
                padding: 16px 20px; border-bottom: 1px solid #2a2a4a; }}
.card-header h2 {{ font-size: 18px; color: #fff; margin-bottom: 6px; }}
.tag {{ display: inline-block; background: #2a2a4a; color: #aaa; padding: 2px 10px; 
        border-radius: 12px; font-size: 12px; margin-right: 6px; }}
.tag.schema {{ background: #1a3a5c; color: #00d2ff; }}
.confidence {{ width: 56px; height: 56px; border-radius: 50%; border: 3px solid; 
               display: flex; align-items: center; justify-content: center; 
               font-weight: bold; font-size: 16px; flex-shrink: 0; }}
.card-body {{ padding: 16px 20px; }}
.meta {{ display: flex; gap: 16px; font-size: 12px; color: #666; margin-bottom: 12px; flex-wrap: wrap; }}
.field {{ margin-bottom: 8px; }}
.field .label {{ display: inline-block; width: 110px; color: #00d2ff; font-size: 13px; }}
details {{ margin-top: 12px; }}
summary {{ cursor: pointer; color: #00d2ff; font-size: 13px; }}
pre {{ background: #0a0a15; padding: 12px; border-radius: 8px; overflow-x: auto; 
       font-size: 12px; color: #ccc; margin-top: 8px; white-space: pre-wrap; }}
footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 32px; }}
a {{ color: #00d2ff; }}
</style>
</head><body>
<div class="container">
    <h1>🔬 Extraction Results</h1>
    <p class="subtitle">Unstructured Text → Structured JSON Pipeline</p>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{success}</div>
            <div class="stat-label">Extractions</div>
        </div>
        <div class="stat">
            <div class="stat-value" style="color: #00d2ff">{avg_conf:.0%}</div>
            <div class="stat-label">Avg Confidence</div>
        </div>
        <div class="stat">
            <div class="stat-value" style="color: #fff">{success}/{success}</div>
            <div class="stat-label">Success Rate</div>
        </div>
    </div>
    
    {cards}
    
    <footer>
        Generated by <a href="https://github.com/manuelarguelles/unstructured-to-json-llm-pipeline">unstructured-to-json-llm-pipeline</a>
        · Model: Llama 3.3 70B (Databricks)
    </footer>
</div>
</body></html>"""


def main():
    html_content = generate_html()
    Path(OUTPUT).write_text(html_content, encoding="utf-8")
    print(f"✅ Report generated: {OUTPUT}")

    if "--no-open" not in sys.argv:
        if platform.system() == "Darwin":
            subprocess.run(["open", OUTPUT])
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", OUTPUT])
        print("📊 Opened in browser")


if __name__ == "__main__":
    main()
