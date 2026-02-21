# google-ads-alert

> Query Google Ads campaign performance daily, flag campaigns where CPA or CPC exceeds your threshold, and post a Slack alert.

**Category:** Marketing / AI  
**Trigger:** Schedule (weekdays at 09:00)  
**Outputs:** Slack alert for over-threshold campaigns + local `ads_report.json`

---

## What it does

Runs each morning, pulls yesterday's campaign-level performance from the Google Ads API (impressions, clicks, cost, conversions), computes CPC and CPA per campaign, then sends a Slack alert listing every campaign that breaches your configured thresholds.

Pairs naturally with the `facebook-ad-ai-analyser` already in this repo — combined they give you cross-platform paid media monitoring.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add a **Google Ads OAuth2** credential (n8n → Credentials → Google Ads)
3. Add a **Slack** credential
4. Set your `customer_id`, `CPA_THRESHOLD_USD`, and `CPC_THRESHOLD_USD` in the Set node
5. Activate the workflow

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. `python workflow.py`

### Running tests (no API keys needed)
```bash
pip install -r requirements.txt
python -m pytest test_workflow.py -v
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads Developer Token (from your API Centre) |
| `GOOGLE_ADS_ACCESS_TOKEN` | OAuth2 access token for your Google Ads account |
| `GOOGLE_ADS_CUSTOMER_ID` | Your 10-digit customer ID (hyphens optional) |
| `CPA_THRESHOLD_USD` | Alert if CPA exceeds this (default: `50.0`) |
| `CPC_THRESHOLD_USD` | Alert if CPC exceeds this (default: `5.0`) |
| `SLACK_BOT_TOKEN` | Slack bot token for posting alerts |
| `SLACK_CHANNEL` | Slack channel to post alerts to (default: `#marketing-alerts`) |
| `OUTPUT_FILE` | Local fallback report path (default: `ads_report.json`) |

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `GOOGLE_ADS_CUSTOMER_ID` | string | Google Ads account/customer ID |
| `CPA_THRESHOLD_USD` | float | Maximum acceptable cost per acquisition |
| `CPC_THRESHOLD_USD` | float | Maximum acceptable cost per click |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `campaign_name` | string | Campaign name |
| `cost_usd` | float | Yesterday's spend in USD |
| `clicks` | int | Click count |
| `conversions` | float | Conversion count |
| `cpc_usd` | float | Computed cost per click |
| `cpa_usd` | float | Computed cost per acquisition |
| `alert_reasons` | list | List of breaching thresholds (if any) |

## Notes / Limitations

- Uses the Google Ads API v16 search stream endpoint — update `GAQL_API_VERSION` in `workflow.py` to match your API version
- OAuth2 access tokens expire after 1 hour. For scheduled use, implement a refresh token flow (see [Google Ads auth docs](https://developers.google.com/google-ads/api/docs/oauth/overview)) or use the n8n version which handles token refresh natively
- CPA is only meaningful if conversion tracking is configured in your Google Ads account — campaigns with 0 conversions will show `cpa_usd: 0.0` and won't trigger CPA alerts
- Manager accounts (MCC): set `GOOGLE_ADS_CUSTOMER_ID` to the individual child account, not the MCC
