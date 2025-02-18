"""
competitor-campaign-monitor

Scrapes a list of competitor landing pages, compares current content
against the previous snapshot, detects changes, and posts a Slack report.

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
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
SLACK_BOT_TOKEN    = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID   = os.getenv("SLACK_CHANNEL_ID", "")
TARGETS_CSV        = os.getenv("TARGETS_CSV", "targets.csv")
SNAPSHOT_FILE      = os.getenv("SNAPSHOT_FILE", "previous_data.json")
DELAY_SECONDS      = float(os.getenv("DELAY_SECONDS", "2"))

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
SCRAPE_HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; competitor-monitor/1.0)"}


# ── Scraping ───────────────────────────────────────────────────────────────────
def scrape_page(url: str) -> dict:
    """Fetch a page and return structured content."""
    try:
        resp = requests.get(url, headers=SCRAPE_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract key fields
        title = soup.title.string.strip() if soup.title else ""
        h1 = soup.find("h1")
        main_heading = h1.get_text(strip=True) if h1 else ""

        # Extract all visible text (cleaned)
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:5000]

        # Try to extract prices
        prices = []
        for el in soup.find_all(string=lambda s: s and "$" in s):
            prices.append(el.strip()[:100])

        return {
            "url": url,
            "title": title,
            "main_heading": main_heading,
            "prices": prices[:5],
            "content_snippet": text[:1000],
            "scraped_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"url": url, "error": str(e), "scraped_at": datetime.utcnow().isoformat()}


# ── AI Analysis ────────────────────────────────────────────────────────────────
def call_openrouter(messages: list) -> str:
    resp = requests.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        json={"model": OPENROUTER_MODEL, "messages": messages},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


ANALYSIS_PROMPT = """You are a Competitor Intelligence Analyst. Compare Current vs Previous page data and detect changes.

Output ONLY a valid JSON object:
{
  "page_context": {"summary": "..."},
  "comparison_analysis": {
    "has_changes": true/false,
    "change_severity": "None|Low|High",
    "price_change": {"detected": true/false, "direction": "Increase|Decrease|Same", "difference_amount": 0.00},
    "content_changes": ["list of specific changes"],
    "verdict": "one-sentence strategic summary"
  }
}"""


def analyse_changes(current: dict, previous: dict | None) -> dict:
    messages = [
        {"role": "system", "content": ANALYSIS_PROMPT},
        {"role": "user", "content": f"Current: {json.dumps(current)}\n\nPrevious: {json.dumps(previous or {})}"},
    ]
    raw = call_openrouter(messages)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])
    return json.loads(raw)


REPORT_PROMPT = """You are a Competitor Intelligence Reporter. Generate a Slack digest from this data.

Output ONLY a JSON array of message objects: [{"slack_text": "..."}]

Rules:
- First message: summary header (how many changes found, severity breakdown)
- One message per changed page (has_changes=true only)
- Use *bold*, 🔴 (High), 🟡 (Low), 🟢 (New)
- Keep each message under 1500 chars"""


def generate_report(all_analyses: list) -> list[dict]:
    messages = [
        {"role": "system", "content": REPORT_PROMPT},
        {"role": "user", "content": json.dumps(all_analyses, indent=2)},
    ]
    raw = call_openrouter(messages)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])
    return json.loads(raw)


# ── Slack ──────────────────────────────────────────────────────────────────────
def send_to_slack(messages: list[dict]):
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        print("[INFO] No Slack credentials — printing report to stdout.")
        for m in messages:
            print(m.get("slack_text", ""))
        return

    client = WebClient(token=SLACK_BOT_TOKEN)
    for m in messages:
        try:
            client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=m.get("slack_text", ""))
            time.sleep(0.5)
        except SlackApiError as e:
            print(f"[ERROR] Slack: {e.response['error']}")


# ── Main ───────────────────────────────────────────────────────────────────────
def load_targets(csv_path: str) -> list[str]:
    urls = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            url = row.get("Page URL", "").strip()
            if url:
                urls.append(url)
    return urls


def load_snapshots() -> dict:
    if Path(SNAPSHOT_FILE).exists():
        with open(SNAPSHOT_FILE) as f:
            return json.load(f)
    return {}


def save_snapshots(data: dict):
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    if not Path(TARGETS_CSV).exists():
        print(f"[ERROR] {TARGETS_CSV} not found.")
        return

    urls = load_targets(TARGETS_CSV)
    snapshots = load_snapshots()
    print(f"[→] Monitoring {len(urls)} URLs")

    all_analyses = []
    new_snapshots = {}

    for url in urls:
        print(f"[→] Scraping: {url}")
        current = scrape_page(url)
        previous = snapshots.get(url)

        print(f"    Analysing changes...")
        analysis = analyse_changes(current, previous)
        analysis["url"] = url
        all_analyses.append(analysis)

        new_snapshots[url] = current
        time.sleep(DELAY_SECONDS)

    # Save new snapshots
    save_snapshots(new_snapshots)
    print(f"[✓] Snapshots saved to {SNAPSHOT_FILE}")

    # Generate and send Slack report
    print("[→] Generating Slack report...")
    report_messages = generate_report(all_analyses)
    send_to_slack(report_messages)
    print("[✓] Report sent.")


if __name__ == "__main__":
    main()
