"""
facebook-ad-ai-analyser

Fetches Facebook ad performance data, calculates account benchmarks,
and uses Google Gemini to score each ad creative.

Usage:
    python workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    Copy .env.example → .env and fill in your values.
"""

import os
import json
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")
FB_AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID", "act_XXXXXXX")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "28"))

FB_API_VERSION = "v22.0"
FB_BASE = f"https://graph.facebook.com/{FB_API_VERSION}"


# ── Facebook API ───────────────────────────────────────────────────────────────
def fetch_ad_insights():
    """Pull last N days of ad-level insights from Facebook."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    params = {
        "level": "ad",
        "fields": "campaign_name,adset_name,ad_name,ad_id,objective,spend,impressions,clicks,actions,action_values,date_start,date_stop",
        "time_range": json.dumps({"since": start_date.strftime("%Y-%m-%d"), "until": end_date.strftime("%Y-%m-%d")}),
        "limit": 500,
        "access_token": FB_ACCESS_TOKEN,
    }
    url = f"{FB_BASE}/{FB_AD_ACCOUNT_ID}/insights"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_action_value(actions, action_types):
    """Extract a count from the Facebook actions array."""
    if not actions:
        return 0
    for t in action_types:
        for a in actions:
            if a.get("action_type") == t:
                return int(a.get("value", 0))
    return 0


def get_purchase_value(action_values, action_types):
    """Extract purchase revenue from action_values array."""
    if not action_values:
        return 0.0
    for t in action_types:
        for a in action_values:
            if a.get("action_type") == t:
                return float(a.get("value", 0))
    return 0.0


def process_raw_ads(raw_ads):
    """Normalise raw Facebook ad data into structured records."""
    ATC_TYPES = ["omni_add_to_cart", "offsite_conversion.fb_pixel_add_to_cart"]
    CHECKOUT_TYPES = ["omni_initiated_checkout", "offsite_conversion.fb_pixel_initiate_checkout"]
    PURCHASE_TYPES = ["omni_purchase", "offsite_conversion.fb_pixel_purchase", "purchase"]

    records = []
    for ad in raw_ads:
        if ad.get("objective") != "OUTCOME_SALES":
            continue
        spend = float(ad.get("spend", 0))
        impressions = int(ad.get("impressions", 0))
        clicks = int(ad.get("clicks", 0))
        purchases = get_action_value(ad.get("actions"), PURCHASE_TYPES)
        purchase_value = get_purchase_value(ad.get("action_values"), PURCHASE_TYPES)
        atc = get_action_value(ad.get("actions"), ATC_TYPES)
        checkouts = get_action_value(ad.get("actions"), CHECKOUT_TYPES)

        records.append({
            "ad_id": ad.get("ad_id"),
            "ad_name": ad.get("ad_name"),
            "campaign_name": ad.get("campaign_name"),
            "objective": ad.get("objective"),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "add_to_carts": atc,
            "checkouts_initiated": checkouts,
            "purchases": purchases,
            "purchase_value": purchase_value,
        })
    return records


def calculate_kpis(records):
    """Aggregate metrics and compute derived KPIs."""
    totals = {k: 0 for k in ["spend", "impressions", "clicks", "add_to_carts",
                               "checkouts_initiated", "purchases", "purchase_value"]}
    for r in records:
        for k in totals:
            totals[k] += r[k]

    kpis = dict(totals)
    kpis["roas"] = round(totals["purchase_value"] / totals["spend"], 2) if totals["spend"] else 0
    kpis["ctr"] = round(totals["clicks"] / totals["impressions"], 4) if totals["impressions"] else 0
    kpis["cpc"] = round(totals["spend"] / totals["clicks"], 2) if totals["clicks"] else 0
    kpis["cost_per_purchase"] = round(totals["spend"] / totals["purchases"], 2) if totals["purchases"] else 0
    kpis["conversion_rate"] = f"{round(totals['purchases'] / totals['clicks'] * 100, 2)}%" if totals["clicks"] else "0%"
    kpis["average_order_value"] = round(totals["purchase_value"] / totals["purchases"], 2) if totals["purchases"] else 0
    return kpis


# ── Gemini AI Analysis ─────────────────────────────────────────────────────────
def analyse_with_ai(ad_data_str, benchmark_str):
    """Send ad data + benchmark to Gemini and return structured analysis."""
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""You are a Senior Facebook Ads Media Buyer. Analyse each ad creative against the account benchmark.

Categorise each ad as one of: HELL YES, YES, MAYBE, NOT REALLY, WE WASTED MONEY, INSUFFICIENT DATA/SPEND

Rules:
- Spend < $50: INSUFFICIENT DATA/SPEND (at best NOT REALLY if poor ratios)
- Spend >= $100 required for YES or HELL YES
- Compare ROAS, Cost Per Purchase, Conversion Rate against benchmark

Return a JSON array. Each item must have:
- ad_id, ad_name, performance_category, justification, recommendation

Ad Data:
{ad_data_str}

Benchmark:
{benchmark_str}

Return ONLY a valid JSON array, no markdown fencing."""

    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    return json.loads(text)


# ── Google Sheets ──────────────────────────────────────────────────────────────
def write_results(records, ai_results):
    """Write raw data and AI insights to Google Sheets."""
    if not SPREADSHEET_ID:
        print("[INFO] No SPREADSHEET_ID set — printing to stdout.")
        for r in ai_results:
            print(r)
        return

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_JSON, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    headers = ["ad_id", "ad_name", "campaign_name", "spend", "impressions", "clicks",
               "purchases", "purchase_value", "performance_category", "justification", "recommendation"]
    sheet.clear()
    sheet.append_row(headers)

    ai_map = {r["ad_id"]: r for r in ai_results}
    for rec in records:
        ai = ai_map.get(rec["ad_id"], {})
        sheet.append_row([
            rec["ad_id"], rec["ad_name"], rec["campaign_name"],
            rec["spend"], rec["impressions"], rec["clicks"],
            rec["purchases"], rec["purchase_value"],
            ai.get("performance_category", ""), ai.get("justification", ""), ai.get("recommendation", "")
        ])
    print(f"[✓] Wrote {len(records)} rows to Google Sheets.")


def main():
    print("[→] Fetching Facebook ad insights...")
    raw = fetch_ad_insights()
    print(f"    {len(raw)} raw ad records")

    records = process_raw_ads(raw)
    print(f"    {len(records)} OUTCOME_SALES ad records")

    if not records:
        print("[WARN] No sales campaign data found.")
        return

    benchmark = calculate_kpis(records)
    print(f"[→] Account benchmark — ROAS: {benchmark['roas']}, CPP: ${benchmark['cost_per_purchase']}")

    print("[→] Sending to Gemini for analysis...")
    ai_results = analyse_with_ai(json.dumps(records, indent=2), json.dumps(benchmark, indent=2))
    print(f"    {len(ai_results)} ads analysed")

    write_results(records, ai_results)
    print("[✓] Done.")


if __name__ == "__main__":
    main()
