# competitor-price-tracker

> Automatically scrape a competitor's pricing page, compare it to your stored data, and update Google Sheets only when something changes.

**Category:** Marketing / Tech  
**Trigger:** Schedule (daily at 9am — configurable)  
**Outputs:** Google Sheet updated only when pricing changes are detected

---

## What it does

Runs daily. Scrapes a competitor's pricing page (default: ClickUp) using an AI agent + Bright Data MCP for reliable extraction. Compares freshly scraped pricing plans against values stored in a Google Sheet. If anything changed, updates the sheet automatically. If nothing changed, does nothing.

Tracks: plan names, prices, and key features for up to 4 pricing tiers.

Great for: competitive intelligence, pricing strategy, alerting on competitor moves, market research.

## Requirements

- **Bright Data MCP** account — [sign up here](https://brightdata.com)
- **OpenAI** API key
- **Google Sheets** set up with pricing columns

## Google Sheet Template

Set up a sheet with columns:  
`1 Plan`, `1 Pricing`, `1 Key Features`, `2 Plan`, `2 Pricing`, `2 Key Features`, `3 Plan`, `3 Pricing`, `3 Key Features`, `4 Plan`, `4 Pricing`, `4 Key Features`

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **OpenAI** and **Bright Data MCP** credentials
3. Add **Google Sheets** OAuth2 credential
4. In the "Set Search Parameters" node, update `url` to the competitor pricing page you want to track
5. Update both Google Sheets node `documentId` values to your sheet
6. Activate

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`
3. `python workflow.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `COMPETITOR_URL` | Pricing page URL to monitor |
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key |
| `SPREADSHEET_ID` | Google Sheet ID to store pricing data |
| `SHEET_NAME` | Sheet tab name (default: `Sheet1`) |

## Extending

- Add a **Slack notification** node after the update step to alert your team when prices change
- Track **multiple competitors** by duplicating the workflow and changing the URL
- Add an **email alert** with the before/after pricing diff
