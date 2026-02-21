# email-performance-reporter

> Pull Mailchimp campaign stats on a schedule and log open rate, click rate, and unsubscribes to a Google Sheet.

**Category:** Marketing  
**Trigger:** Schedule (weekly — every Monday at 08:00)  
**Outputs:** One row per campaign appended to Google Sheets (or saved locally as `report.json`)

---

## What it does

Runs weekly, fetches your last N sent Mailchimp campaigns, computes the core engagement metrics, and pushes a summary row to Google Sheets via an n8n HTTP Request node (or your own webhook). Useful for keeping a running history of email performance without logging into Mailchimp every Monday.

Metrics captured per campaign:

| Metric | Description |
|--------|-------------|
| `open_rate_pct` | Unique opens ÷ recipients × 100 |
| `click_rate_pct` | Unique clicks ÷ recipients × 100 |
| `unsubscribe_rate_pct` | Unsubscribes ÷ recipients × 100 |

## Setup

### n8n
1. Import `workflow.json` into your n8n instance
2. Add your **Mailchimp API credential** (n8n → Credentials → Mailchimp API)
3. Set your **Google Sheets credential** and update the sheet ID in the Google Sheets node
4. Adjust `CAMPAIGN_LIMIT` in the Set node if you want more/fewer campaigns
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
| `MAILCHIMP_API_KEY` | Your Mailchimp API key (Account → Extras → API keys) |
| `MAILCHIMP_SERVER` | Your data centre prefix, e.g. `us1`, `us6` (from API key suffix) |
| `MAILCHIMP_LIST_ID` | Optional — filter to a specific audience ID |
| `CAMPAIGN_LIMIT` | Number of recent campaigns to pull (default: `10`) |
| `SHEETS_WEBHOOK_URL` | n8n webhook URL that appends a row to Google Sheets |
| `OUTPUT_FILE` | Local fallback output path (default: `report.json`) |

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `MAILCHIMP_LIST_ID` | string | Optional audience filter |
| `CAMPAIGN_LIMIT` | int | How many sent campaigns to retrieve |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `campaign_id` | string | Mailchimp campaign ID |
| `subject_line` | string | Email subject line |
| `send_time` | string | ISO 8601 send timestamp |
| `recipients` | int | Total recipients |
| `open_rate_pct` | float | Unique open rate % |
| `click_rate_pct` | float | Unique click rate % |
| `unsubscribe_rate_pct` | float | Unsubscribe rate % |

## Notes / Limitations

- Mailchimp's free plan includes full Campaigns API access — no paid plan required
- `report_summary` on very recent campaigns may be `{}` until Mailchimp finalises stats (usually within a few hours of send)
- The Python script writes `report.json` locally as a fallback; in production, configure `SHEETS_WEBHOOK_URL` to push to Sheets
- No deduplication — if you run this twice in a week you'll get duplicate rows for the same campaigns. Either use the n8n version (which can check for existing rows) or add a column-based dedup step
