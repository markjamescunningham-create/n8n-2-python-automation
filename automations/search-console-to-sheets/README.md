# search-console-to-sheets

> Pull keyword, page, and date performance data from Google Search Console and sync it to Google Sheets on a schedule.

**Category:** Marketing / Tech  
**Trigger:** Schedule (configurable — default: daily)  
**Outputs:** Three Google Sheets tabs updated: Queries, Pages, Dates

---

## What it does

On a schedule, fetches Search Console performance data for a configured domain across three dimensions:
- **Queries** — top keywords driving impressions and clicks
- **Pages** — top pages by traffic
- **Dates** — daily click/impression trends

Data is written to a Google Sheet (upsert: updates existing rows, appends new ones). Each row includes: keyword/page/date, clicks, impressions, CTR, and average position.

Great for: SEO reporting, content performance tracking, weekly marketing dashboards, agency client reporting.

## Google Sheet Template

Copy this template:  
[Search Console Reports Sheet](https://docs.google.com/spreadsheets/d/10hSuGOOf14YvVY2Bw8WXUIpsyXO614l7qNEjkyVY_Qg/edit?usp=sharing)

The sheet has three tabs: **Query**, **PAGES**, **Dates**

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **Google OAuth2** credential with these scopes:
   - `https://www.googleapis.com/auth/webmasters`
   - `https://www.googleapis.com/auth/webmasters.readonly`
3. Add **Google Sheets** OAuth2 credential
4. In the "Set your domain" node, update `domain` (e.g. `yourdomain.com`) and `days` (lookback window)
5. Update the `documentId` values in the three Google Sheets nodes to your sheet
6. Adjust the Schedule Trigger as needed
7. Activate

### Python
1. `pip install -r requirements.txt`
2. Create a Google service account with Search Console and Sheets access
3. Copy `.env.example` → `.env` and fill in values
4. `python workflow.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CREDENTIALS_JSON` | Path to service account JSON key |
| `DOMAIN` | Your Search Console domain (e.g. `yourdomain.com`) |
| `DAYS` | Number of days to look back (default: `30`) |
| `SPREADSHEET_ID` | Google Sheet ID to write results to |

## Notes

- The Google Search Console API uses `sc-domain:yourdomain.com` format for domain properties
- Data returned is capped at 1000 rows per dimension by default (adjust `rowLimit` in the API body if needed)
- CTR is returned as a decimal (e.g. `0.045` = 4.5%)
