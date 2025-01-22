# keyword-rank-tracker

> Enter a keyword and automatically track the top 5 Google SERP results on a schedule, logging everything to Google Sheets.

**Category:** Marketing / Tech  
**Trigger:** Schedule (daily at 9am — configurable)  
**Outputs:** Rank, title, URL, and description for top 5 results logged to Google Sheets

---

## What it does

Runs on a schedule. For a configured keyword, uses an AI agent powered by Bright Data MCP to scrape the top 5 Google search results (bypassing CAPTCHAs and bot detection). Results are structured with an output parser and written to Google Sheets.

Tracks: `rank`, `title`, `url`, `description` per result, per run.

Great for: SEO monitoring, tracking competitor rankings, content gap analysis, campaign performance tracking.

## Requirements

- **Bright Data MCP** account with Search Console access — [sign up here](https://brightdata.com)
- **OpenAI** API key
- **Google Sheets** with columns: Title, URL, Description, Rank

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **OpenAI** credential
3. Add **Bright Data MCP** credential in n8n
4. In the "Input: Keyword & Domain" node, update the `keyword` value
5. Update the Google Sheets `documentId` to your tracking sheet
6. Adjust the Schedule Trigger as needed
7. Activate

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. Run: `python workflow.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | Model (default: `gpt-4o-mini`) |
| `KEYWORD` | Keyword to track (e.g. `best running shoes`) |
| `SERP_API_KEY` | SerpAPI key (Python version uses SerpAPI instead of Bright Data) |
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key |
| `SPREADSHEET_ID` | Google Sheet to log results to |
| `SHEET_NAME` | Sheet tab name (default: `Sheet1`) |

## Notes

- The n8n version uses **Bright Data MCP** for accurate, undetectable scraping
- The Python version uses **SerpAPI** as a simpler alternative (`pip install google-search-results`)
- Results are appended per run — you build up a history of ranking changes over time
