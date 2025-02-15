"""
b2b-lead-researcher

Scrapes a list of company pages, analyses content with AI,
and creates structured Airtable records for each company.

Usage:
    python workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    Copy .env.example → .env and fill in your values.
"""

import os
import json
import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pyairtable import Api

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
AIRTABLE_TOKEN     = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID   = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE_ID  = os.getenv("AIRTABLE_TABLE_ID", "")
TARGETS_CSV        = os.getenv("TARGETS_CSV", "targets.csv")
DELAY_SECONDS      = float(os.getenv("DELAY_SECONDS", "2"))

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
HEADERS_SCRAPE  = {"User-Agent": "Mozilla/5.0 (compatible; b2b-researcher/1.0)"}


# ── Scraping ───────────────────────────────────────────────────────────────────
def scrape_page(url: str) -> str:
    """Fetch a page and return cleaned text content."""
    try:
        resp = requests.get(url, headers=HEADERS_SCRAPE, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:8000]  # Limit to avoid token limits
    except Exception as e:
        return f"[Scrape error: {e}]"


# ── AI Analysis ────────────────────────────────────────────────────────────────
def call_openrouter(messages: list, model: str = None) -> str:
    """Call OpenRouter chat completion API."""
    resp = requests.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        json={"model": model or OPENROUTER_MODEL, "messages": messages},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


PAGE_ANALYSIS_PROMPT = """You are a Senior B2B Market Analyst. Analyse the following scraped page content.

Detect whether it's "News/Changelog" or "Company Profile" and extract:
- data_type: "News" or "Profile"
- company_name
- primary_date (YYYY-MM-DD or today's date)
- core_summary (2-3 sentences)
- key_entities (comma-separated: founders, product names, tech)
- strategic_focus (one sentence)
- raw_content_snippet (first 300 chars of main content)

Return ONLY a valid JSON object, no markdown fencing."""


SYNTHESIS_PROMPT = """You are an Expert B2B Lead Researcher. Synthesise the following array of page analyses 
for a single company into a single Airtable record.

Create:
- Name: company name
- Notes: Markdown with sections: Company Persona, Strategic Focus, Recent Activities, Key Tech
- Attachment_Summary: 1-sentence executive bio

Return ONLY a valid JSON object with keys: Name, Notes, Attachment_Summary"""


def analyse_page(url: str, content: str) -> dict:
    """Analyse a single page with AI."""
    messages = [
        {"role": "system", "content": PAGE_ANALYSIS_PROMPT},
        {"role": "user", "content": f"URL: {url}\n\nContent:\n{content}"},
    ]
    raw = call_openrouter(messages)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])
    return json.loads(raw)


def synthesise_company(pages: list[dict]) -> dict:
    """Synthesise multiple page analyses into a single company record."""
    messages = [
        {"role": "system", "content": SYNTHESIS_PROMPT},
        {"role": "user", "content": json.dumps(pages, indent=2)},
    ]
    raw = call_openrouter(messages)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])
    return json.loads(raw)


# ── Airtable ───────────────────────────────────────────────────────────────────
def create_airtable_record(record: dict):
    """Create a new record in Airtable."""
    api = Api(AIRTABLE_TOKEN)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID)
    table.create({
        "Name": record.get("Name", ""),
        "Notes": record.get("Notes", ""),
        "Status": "Todo",
        "Attachment Summary": record.get("Attachment_Summary", ""),
    })


# ── Main ───────────────────────────────────────────────────────────────────────
def load_targets(csv_path: str) -> dict[str, list[str]]:
    """Load URLs from CSV. Groups by company (uses domain as key if no Company column)."""
    from urllib.parse import urlparse
    companies = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("Page URL", "").strip()
            if not url:
                continue
            company = row.get("Company", urlparse(url).netloc.replace("www.", ""))
            companies.setdefault(company, []).append(url)
    return companies


def main():
    if not Path(TARGETS_CSV).exists():
        print(f"[ERROR] {TARGETS_CSV} not found. Create a CSV with a 'Page URL' column.")
        return

    companies = load_targets(TARGETS_CSV)
    print(f"[→] Found {sum(len(v) for v in companies.values())} URLs across {len(companies)} companies")

    for company, urls in companies.items():
        print(f"\n[→] Processing: {company} ({len(urls)} pages)")
        page_analyses = []

        for url in urls:
            print(f"    Scraping: {url}")
            content = scrape_page(url)
            print(f"    Analysing...")
            analysis = analyse_page(url, content)
            page_analyses.append(analysis)
            time.sleep(DELAY_SECONDS)

        print(f"    Synthesising {len(page_analyses)} pages...")
        record = synthesise_company(page_analyses)
        record["Name"] = record.get("Name") or company

        if AIRTABLE_TOKEN and AIRTABLE_BASE_ID:
            create_airtable_record(record)
            print(f"    [✓] Created Airtable record for {record['Name']}")
        else:
            print(f"    [INFO] No Airtable credentials — record would be:")
            print(json.dumps(record, indent=2))

    print("\n[✓] Done.")


if __name__ == "__main__":
    main()
