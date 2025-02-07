"""
multi-page-web-scraper

Configurable recursive web scraper. Fetches pages using CSS selectors,
automatically follows pagination, and writes results to Google Sheets.

Usage:
    python workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    Copy .env.example → .env and fill in your values.
"""

import os
import time
import csv
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
START_URL = os.getenv("START_URL", "https://quotes.toscrape.com/tag/humor/")
NEXT_PAGE_SELECTOR = os.getenv("NEXT_PAGE_SELECTOR", "li.next a")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "1"))

# Define fields to extract — edit this list to match your target site
FIELDS = [
    {"name": "author", "selector": "span > small.author", "type": "text"},
    {"name": "text",   "selector": "span.text",           "type": "text"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; n8n-scraper/1.0)"
}


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch a URL and return a BeautifulSoup object."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_fields(soup: BeautifulSoup, fields: list) -> list[dict]:
    """
    Extract field values from all matching containers on the page.
    Each field definition: { name, selector, type } where type is 'text' or an attribute name.
    Returns a list of dicts — one per matched group.
    """
    # Find the max number of matches across all fields to know how many rows we have
    field_results = {}
    for field in fields:
        elements = soup.select(field["selector"])
        if field["type"] == "text":
            field_results[field["name"]] = [el.get_text(strip=True) for el in elements]
        else:
            field_results[field["name"]] = [el.get(field["type"], "") for el in elements]

    if not field_results:
        return []

    max_count = max(len(v) for v in field_results.values())
    rows = []
    for i in range(max_count):
        row = {k: (v[i] if i < len(v) else "") for k, v in field_results.items()}
        rows.append(row)
    return rows


def get_next_page_url(soup: BeautifulSoup, current_url: str, selector: str) -> str | None:
    """Extract the next page URL using the CSS selector."""
    el = soup.select_one(selector)
    if not el:
        return None
    href = el.get("href", "")
    if not href:
        return None
    return urljoin(current_url, href)


def write_to_sheets(rows: list[dict], field_names: list[str]):
    """Append rows to Google Sheets."""
    if not SPREADSHEET_ID:
        print("[INFO] No SPREADSHEET_ID set — printing results to stdout instead.")
        for row in rows:
            print(row)
        return

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_JSON, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    # Write header if sheet is empty
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(field_names)

    for row in rows:
        sheet.append_row([row.get(f, "") for f in field_names])

    print(f"[✓] Wrote {len(rows)} rows to Google Sheets.")


def main():
    url = START_URL
    all_rows = []
    page_num = 1
    field_names = [f["name"] for f in FIELDS]

    while url:
        print(f"[→] Scraping page {page_num}: {url}")
        soup = fetch_page(url)

        rows = extract_fields(soup, FIELDS)
        all_rows.extend(rows)
        print(f"    Found {len(rows)} items (total: {len(all_rows)})")

        next_url = get_next_page_url(soup, url, NEXT_PAGE_SELECTOR)
        if next_url == url:
            break  # Guard against infinite loop
        url = next_url
        page_num += 1

        if url:
            time.sleep(DELAY_SECONDS)

    print(f"\n[✓] Scraping complete — {len(all_rows)} total rows across {page_num} pages.")
    write_to_sheets(all_rows, field_names)


if __name__ == "__main__":
    main()
