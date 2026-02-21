"""
email-performance-reporter

Pulls the last N campaigns from Mailchimp, computes open rate, click rate,
and unsubscribe rate, then appends a summary row to a Google Sheet.

Usage:
    python workflow.py

Schedule with cron (e.g. every Monday at 08:00):
    0 8 * * 1 /usr/bin/python3 /path/to/workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import os
import json
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
MAILCHIMP_API_KEY   = os.getenv("MAILCHIMP_API_KEY", "")
MAILCHIMP_SERVER    = os.getenv("MAILCHIMP_SERVER", "us1")   # e.g. us1, us6
MAILCHIMP_LIST_ID   = os.getenv("MAILCHIMP_LIST_ID", "")
CAMPAIGN_LIMIT      = int(os.getenv("CAMPAIGN_LIMIT", "10"))

SHEETS_WEBHOOK_URL  = os.getenv("SHEETS_WEBHOOK_URL", "")    # n8n webhook → Sheets
OUTPUT_FILE         = os.getenv("OUTPUT_FILE", "report.json")


# ── Mailchimp ──────────────────────────────────────────────────────────────────
def fetch_campaigns() -> list[dict]:
    """Return the last CAMPAIGN_LIMIT sent campaigns from Mailchimp."""
    if not MAILCHIMP_API_KEY:
        print("[SKIP] MAILCHIMP_API_KEY not set — skipping Mailchimp fetch.")
        return []

    url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0/campaigns"
    params = {
        "status": "sent",
        "count":  CAMPAIGN_LIMIT,
        "sort_field": "send_time",
        "sort_dir": "DESC",
    }
    if MAILCHIMP_LIST_ID:
        params["list_id"] = MAILCHIMP_LIST_ID

    resp = requests.get(
        url,
        params=params,
        auth=("anystring", MAILCHIMP_API_KEY),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("campaigns", [])


# ── Metrics extraction ─────────────────────────────────────────────────────────
def extract_metrics(campaign: dict) -> dict:
    """Pull the key performance fields out of a Mailchimp campaign object."""
    report = campaign.get("report_summary", {})
    settings = campaign.get("settings", {})

    recipients   = report.get("subscriber_count", 0) or 0
    opens        = report.get("unique_opens", 0) or 0
    clicks       = report.get("unique_clicks", 0) or 0
    unsubscribes = report.get("unsubscribed", 0) or 0

    open_rate        = round(opens / recipients * 100, 2)        if recipients else 0.0
    click_rate       = round(clicks / recipients * 100, 2)       if recipients else 0.0
    unsubscribe_rate = round(unsubscribes / recipients * 100, 2) if recipients else 0.0

    return {
        "campaign_id":        campaign.get("id", ""),
        "subject_line":       settings.get("subject_line", ""),
        "send_time":          campaign.get("send_time", ""),
        "recipients":         recipients,
        "opens":              opens,
        "clicks":             clicks,
        "unsubscribes":       unsubscribes,
        "open_rate_pct":      open_rate,
        "click_rate_pct":     click_rate,
        "unsubscribe_rate_pct": unsubscribe_rate,
        "retrieved_at":       datetime.now(timezone.utc).isoformat(),
    }


# ── Output ─────────────────────────────────────────────────────────────────────
def send_to_sheets(rows: list[dict]) -> None:
    """POST rows to a Google Sheets via an n8n webhook (or any HTTP endpoint)."""
    if not SHEETS_WEBHOOK_URL:
        print("[SKIP] SHEETS_WEBHOOK_URL not set — skipping Sheets push.")
        return

    resp = requests.post(
        SHEETS_WEBHOOK_URL,
        json={"rows": rows},
        timeout=15,
    )
    resp.raise_for_status()
    print(f"[✓] Pushed {len(rows)} row(s) to Sheets.")


def save_to_file(rows: list[dict]) -> None:
    """Save the report rows to a local JSON file as a fallback."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"[✓] Saved report to {OUTPUT_FILE}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> list[dict]:
    print(f"[→] Fetching last {CAMPAIGN_LIMIT} Mailchimp campaigns...")
    campaigns = fetch_campaigns()

    if not campaigns:
        print("[!] No campaigns returned.")
        return []

    rows = [extract_metrics(c) for c in campaigns]
    print(f"[✓] Processed {len(rows)} campaign(s).")

    # Print summary table
    for r in rows:
        print(
            f"  {r['send_time'][:10]}  {r['subject_line'][:40]:<40}  "
            f"OR: {r['open_rate_pct']:5.1f}%  CR: {r['click_rate_pct']:5.1f}%"
        )

    send_to_sheets(rows)
    save_to_file(rows)
    return rows


if __name__ == "__main__":
    main()
