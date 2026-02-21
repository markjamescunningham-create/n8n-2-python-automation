"""
google-ads-alert

Queries the Google Ads API for campaign performance (yesterday's data),
flags campaigns where CPA or CPC exceeds a configured threshold, and
posts an alert to Slack if any campaigns are over-budget.

Usage:
    python workflow.py

Schedule with cron (e.g. every weekday at 09:00):
    0 9 * * 1-5 /usr/bin/python3 /path/to/workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import os
import json
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
GOOGLE_ADS_DEVELOPER_TOKEN  = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_ACCESS_TOKEN     = os.getenv("GOOGLE_ADS_ACCESS_TOKEN", "")  # OAuth2 bearer
GOOGLE_ADS_CUSTOMER_ID      = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")

CPA_THRESHOLD_USD   = float(os.getenv("CPA_THRESHOLD_USD", "50.0"))
CPC_THRESHOLD_USD   = float(os.getenv("CPC_THRESHOLD_USD", "5.0"))

SLACK_BOT_TOKEN     = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL       = os.getenv("SLACK_CHANNEL", "#marketing-alerts")
OUTPUT_FILE         = os.getenv("OUTPUT_FILE", "ads_report.json")

GAQL_API_VERSION    = "v16"


# ── Google Ads query ────────────────────────────────────────────────────────────
def build_gaql_query(report_date: str) -> str:
    """Build the Google Ads Query Language (GAQL) string for campaign performance."""
    return f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            segments.date
        FROM campaign
        WHERE segments.date = '{report_date}'
          AND campaign.status = 'ENABLED'
        ORDER BY metrics.cost_micros DESC
    """


def fetch_campaign_performance(report_date: str | None = None) -> list[dict]:
    """Call the Google Ads API and return raw campaign rows."""
    if not GOOGLE_ADS_DEVELOPER_TOKEN or not GOOGLE_ADS_ACCESS_TOKEN:
        print("[SKIP] Google Ads credentials not set — skipping API fetch.")
        return []
    if not GOOGLE_ADS_CUSTOMER_ID:
        print("[SKIP] GOOGLE_ADS_CUSTOMER_ID not set.")
        return []

    if report_date is None:
        report_date = (date.today() - timedelta(days=1)).isoformat()

    url = (
        f"https://googleads.googleapis.com/{GAQL_API_VERSION}/"
        f"customers/{GOOGLE_ADS_CUSTOMER_ID}/googleAds:searchStream"
    )
    headers = {
        "Authorization":         f"Bearer {GOOGLE_ADS_ACCESS_TOKEN}",
        "developer-token":       GOOGLE_ADS_DEVELOPER_TOKEN,
        "Content-Type":          "application/json",
    }
    body = {"query": build_gaql_query(report_date)}

    resp = requests.post(url, headers=headers, json=body, timeout=20)
    resp.raise_for_status()

    rows = []
    for chunk in resp.json():
        for result in chunk.get("results", []):
            rows.append(result)
    return rows


# ── Metrics normalisation ──────────────────────────────────────────────────────
def normalise_row(raw: dict) -> dict:
    """Convert a raw GAQL result into a flat, human-readable dict."""
    campaign  = raw.get("campaign", {})
    metrics   = raw.get("metrics", {})
    segment   = raw.get("segments", {})

    cost_usd     = int(metrics.get("costMicros", 0)) / 1_000_000
    clicks       = int(metrics.get("clicks", 0))
    conversions  = float(metrics.get("conversions", 0))

    cpc = round(cost_usd / clicks,       2) if clicks       else 0.0
    cpa = round(cost_usd / conversions,  2) if conversions  else 0.0

    return {
        "campaign_id":   campaign.get("id", ""),
        "campaign_name": campaign.get("name", ""),
        "status":        campaign.get("status", ""),
        "date":          segment.get("date", ""),
        "impressions":   int(metrics.get("impressions", 0)),
        "clicks":        clicks,
        "cost_usd":      round(cost_usd, 2),
        "conversions":   conversions,
        "cpc_usd":       cpc,
        "cpa_usd":       cpa,
    }


# ── Threshold check ────────────────────────────────────────────────────────────
def find_over_threshold(rows: list[dict]) -> list[dict]:
    """Return campaigns where CPA or CPC exceeds the configured thresholds."""
    flagged = []
    for r in rows:
        reasons = []
        if r["cpa_usd"] and r["cpa_usd"] > CPA_THRESHOLD_USD:
            reasons.append(f"CPA ${r['cpa_usd']:.2f} > ${CPA_THRESHOLD_USD:.2f}")
        if r["cpc_usd"] and r["cpc_usd"] > CPC_THRESHOLD_USD:
            reasons.append(f"CPC ${r['cpc_usd']:.2f} > ${CPC_THRESHOLD_USD:.2f}")
        if reasons:
            flagged.append({**r, "alert_reasons": reasons})
    return flagged


# ── Slack alert ────────────────────────────────────────────────────────────────
def send_slack_alert(flagged: list[dict]) -> None:
    """Post an over-threshold alert to Slack."""
    if not SLACK_BOT_TOKEN:
        print("[SKIP] SLACK_BOT_TOKEN not set — printing alert instead.")
        for f in flagged:
            print(f"  ⚠️  {f['campaign_name']}: {', '.join(f['alert_reasons'])}")
        return
    if not flagged:
        return

    lines = [f"*🚨 Google Ads Alert — {flagged[0]['date']}*\n"]
    for f in flagged:
        reasons_str = " | ".join(f["alert_reasons"])
        lines.append(f"• *{f['campaign_name']}* — {reasons_str}")

    text = "\n".join(lines)
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": SLACK_CHANNEL, "text": text},
        timeout=10,
    )
    resp.raise_for_status()
    if not resp.json().get("ok"):
        print(f"[!] Slack error: {resp.json().get('error')}")
    else:
        print(f"[✓] Slack alert sent to {SLACK_CHANNEL}.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> dict:
    report_date = (date.today() - timedelta(days=1)).isoformat()
    print(f"[→] Fetching Google Ads performance for {report_date}...")

    raw_rows  = fetch_campaign_performance(report_date)
    rows      = [normalise_row(r) for r in raw_rows]

    print(f"[✓] {len(rows)} campaign(s) retrieved.")
    for r in rows:
        print(
            f"  {r['campaign_name']:<40}  "
            f"Spend: ${r['cost_usd']:7.2f}  "
            f"CPC: ${r['cpc_usd']:5.2f}  "
            f"CPA: ${r['cpa_usd']:7.2f}"
        )

    flagged = find_over_threshold(rows)
    if flagged:
        print(f"\n[!] {len(flagged)} campaign(s) over threshold — sending alert.")
        send_slack_alert(flagged)
    else:
        print("\n[✓] All campaigns within thresholds.")

    result = {"date": report_date, "campaigns": rows, "flagged": flagged}

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[✓] Report saved to {OUTPUT_FILE}")

    return result


if __name__ == "__main__":
    main()
