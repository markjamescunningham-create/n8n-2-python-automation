# facebook-ad-ai-analyser

> Pull 28 days of Facebook ad performance data, calculate account-wide benchmarks, and use an AI media buyer (Google Gemini) to score each ad creative as "HELL YES", "YES", "MAYBE", or "WE WASTED MONEY" — all written back to Google Sheets.

> **Status:** Works well in n8n. Python version is functional but missing the token auto-refresh — you'll need to manually update your access token every 60 days.

**Category:** AI / Marketing  
**Trigger:** Manual (or convert to scheduled)  
**Outputs:** Google Sheet updated with raw metrics + AI performance category, justification, and recommendation per ad

---

## What it does

1. **Token Management** — Retrieves your Facebook long-term access token from NocoDB and auto-refreshes it if expiry is within 3 days
2. **Fetch Ad Data** — Calls the Facebook Graph API for ad-level performance (last 28 days): spend, impressions, clicks, add-to-carts, checkouts, purchases, purchase value
3. **Process & Filter** — Parses raw Facebook action arrays, filters for `OUTCOME_SALES` campaigns only, aggregates metrics per ad creative
4. **Benchmark Calculation** — Computes account-wide KPIs: average ROAS, Cost Per Purchase, CTR, conversion rate — used as the AI comparison baseline
5. **AI Analysis** — Google Gemini (`gemini-2.5-pro`) acts as a Senior Media Buyer, comparing each ad against the benchmark using strict spend thresholds and categorising it with a justification and recommendation
6. **Write to Sheets** — Outputs raw data and AI insights to a single Google Sheet, matched by `ad_id`

**Performance categories:**
- 🟢 **HELL YES** — Spend ≥ $100, dramatically outperforms benchmarks
- ✅ **YES** — Spend ≥ $100, clearly outperforms benchmarks
- 🟡 **MAYBE** — Spend ≥ $50, mixed results or insufficient data for confidence
- ❌ **NOT REALLY** — Underperforming vs benchmarks
- 💸 **WE WASTED MONEY** — Significant spend, poor ROAS, pause candidate
- ⏳ **INSUFFICIENT DATA/SPEND** — Spend < $50

## Setup

### n8n
1. Import `workflow.json` into n8n
2. **Facebook token**: Set up a NocoDB table to store your `longTermAccessToken` and `end_date`, then connect the `Getting Long-Term Token` node — OR replace this section with your preferred credential store
3. Update the `Getting Data For the Past 28 Days...` node URL: replace `act_XXXXXX` with your Facebook Ad Account ID
4. Add **Google Gemini** credential to the `Google Gemini Chat Model` node
5. Add **Google Sheets** OAuth credential to both Sheets nodes
6. In both Google Sheets nodes, replace `XXXX` in the Document ID with your Google Sheet ID
7. Click **Test workflow**

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`
3. `python workflow.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FB_ACCESS_TOKEN` | Facebook long-term access token |
| `FB_AD_ACCOUNT_ID` | Facebook Ad Account ID (e.g. `act_123456789`) |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Model name (default: `gemini-2.0-flash`) |
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key (for Sheets) |
| `SPREADSHEET_ID` | Google Sheet ID to write results |
| `SHEET_NAME` | Sheet tab name (default: `Sheet1`) |
| `LOOKBACK_DAYS` | Days of data to fetch (default: `28`) |

## Google Sheet Columns

**Required headers (exactly):**
`ad_id`, `ad_name`, `objective`, `total_spend`, `total_impressions`, `total_clicks`, `total_add_to_carts`, `total_checkouts_initiated`, `total_purchases`, `total_purchase_value`, `ctr`, `cpc`, `cpm`, `cost_per_add_to_cart`, `cost_per_checkout`, `cost_per_purchase`, `roas`, `average_order_value`, `conversion_rate`, `Best Performing Ad`, `Justification`, `Recommendation`

## Known Issues / TODO

- **No API pagination in Python version** — `fetch_ad_insights()` has a hardcoded `limit=500`. If your account has more than 500 ads in the 28-day window you'll silently miss results. The Facebook API returns a `paging.next` cursor but I haven't wired that up yet.
- **Python version has no token refresh** — the n8n workflow handles token lifecycle via NocoDB. The Python script just reads `FB_ACCESS_TOKEN` from `.env`. Long-lived tokens last ~60 days, so this bites you eventually.
- **AI output sometimes has JSON formatting issues** — Gemini occasionally wraps the response in markdown fencing despite the prompt saying not to. The script strips it, but if the model changes behaviour this will break on `json.loads()`. Could add a more robust fallback parser.
- **Clears the entire sheet on each run** — `write_results()` does `sheet.clear()` before writing. This is intentional (fresh analysis each time) but means you lose historical runs. Add a dated tab per run if you want history.

## Notes

- The AI prompt uses strict spend thresholds to prevent mis-categorising ads with too little data — tweak these in the `Senior Facebook Ads Media Buyer` node if your account has different spend levels
- The token auto-refresh in n8n requires NocoDB — replace with any key-value store or n8n's built-in credential store if preferred
- The Python version uses a simple direct Facebook API call and the Gemini API directly, without the NocoDB token management layer
