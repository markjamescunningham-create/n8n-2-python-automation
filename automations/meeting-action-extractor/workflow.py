"""
meeting-action-extractor

Takes a meeting transcript (text file or stdin), sends it to OpenAI,
and extracts structured action items: owner, task description, and due date.
Saves results to CSV and optionally pushes them to a Notion database.

Usage:
    python workflow.py --transcript meeting.txt
    cat meeting.txt | python workflow.py   # stdin mode
    python workflow.py                     # reads TRANSCRIPT_FILE from .env

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TRANSCRIPT_FILE  = os.getenv("TRANSCRIPT_FILE", "")
OUTPUT_CSV       = os.getenv("OUTPUT_CSV", "action_items.csv")

# Notion (optional)
NOTION_API_KEY   = os.getenv("NOTION_API_KEY", "")
NOTION_DB_ID     = os.getenv("NOTION_DB_ID", "")


# ── Transcript loading ─────────────────────────────────────────────────────────
def load_transcript(filepath: str | None = None) -> str:
    """Load transcript text from a file path, stdin, or env-configured path."""
    if filepath:
        with open(filepath) as f:
            return f.read()
    if TRANSCRIPT_FILE:
        with open(TRANSCRIPT_FILE) as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError(
        "No transcript provided. Supply --transcript <file>, pipe via stdin, "
        "or set TRANSCRIPT_FILE in .env."
    )


# ── Extraction ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an executive assistant analysing meeting transcripts.
Extract every action item mentioned and return a JSON array.
Each item must have these fields:
  - "owner":       string — first name or full name of the person responsible (use "Unassigned" if unclear)
  - "task":        string — concise description of what needs to be done
  - "due_date":    string — ISO 8601 date if mentioned (e.g. "2024-03-15"), else null
  - "priority":    string — "High", "Medium", or "Low" based on context
  - "context":     string — one sentence of context from the meeting

Return only a valid JSON array with no markdown fences.
If there are no action items, return an empty array [].
""".strip()


def extract_action_items(transcript: str) -> list[dict]:
    """Send the transcript to OpenAI and return parsed action items."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Check your .env file.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Meeting transcript:\n\n{transcript}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = response.choices[0].message.content

    parsed = json.loads(raw)
    # The model may return {"action_items": [...]} or just [...]
    if isinstance(parsed, dict):
        for key in ("action_items", "items", "actions"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        # Fall back to first list value found
        for v in parsed.values():
            if isinstance(v, list):
                return v
        return []
    if isinstance(parsed, list):
        return parsed
    return []


# ── Output ─────────────────────────────────────────────────────────────────────
FIELDNAMES = ["owner", "task", "due_date", "priority", "context", "extracted_at"]


def save_to_csv(items: list[dict], filepath: str = OUTPUT_CSV) -> str:
    """Append action items to a CSV file. Creates the file if it doesn't exist."""
    extracted_at = datetime.now(timezone.utc).isoformat()
    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for item in items:
            writer.writerow({**item, "extracted_at": extracted_at})

    return filepath


def push_to_notion(items: list[dict]) -> None:
    """Push each action item as a page to a Notion database."""
    if not NOTION_API_KEY or not NOTION_DB_ID:
        print("[SKIP] NOTION_API_KEY or NOTION_DB_ID not set — skipping Notion push.")
        return

    headers = {
        "Authorization":  f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type":   "application/json",
    }

    for item in items:
        page = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Name":     {"title":    [{"text": {"content": item.get("task", "")}}]},
                "Owner":    {"rich_text":[{"text": {"content": item.get("owner", "Unassigned")}}]},
                "Due Date": {"date":     {"start": item["due_date"]} if item.get("due_date") else None},
                "Priority": {"select":   {"name": item.get("priority", "Medium")}},
                "Context":  {"rich_text":[{"text": {"content": item.get("context", "")}}]},
            },
        }
        # Remove properties where the value (or the inner date) is None
        page["properties"] = {
            k: v for k, v in page["properties"].items()
            if v is not None and not (isinstance(v, dict) and v.get("date") is None)
        }

        resp = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=page,
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"  [✓] Notion page created: {item.get('task', '')[:60]}")
        else:
            print(f"  [!] Notion error for '{item.get('task', '')}': {resp.text[:200]}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main(transcript_path: str | None = None) -> list[dict]:
    transcript = load_transcript(transcript_path)

    print(f"[→] Transcript loaded ({len(transcript)} characters).")
    print("[→] Extracting action items with OpenAI...")

    items = extract_action_items(transcript)

    if not items:
        print("[!] No action items found in transcript.")
        return []

    print(f"[✓] {len(items)} action item(s) extracted:\n")
    for i, item in enumerate(items, 1):
        due = item.get("due_date") or "No date"
        print(f"  {i}. [{item.get('priority','?')}] {item.get('owner','?')}: {item.get('task', '')}")
        print(f"     Due: {due}")

    csv_path = save_to_csv(items)
    print(f"\n[✓] Saved to {csv_path}")

    push_to_notion(items)

    return items


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract action items from a meeting transcript.")
    parser.add_argument("--transcript", type=str, help="Path to transcript text file")
    args = parser.parse_args()
    main(transcript_path=args.transcript)
