# multi-page-web-scraper

> A configurable, recursive web scraper that automatically follows pagination and extracts structured data using CSS selectors — no code changes needed between targets.

**Category:** Tech  
**Trigger:** Manual  
**Outputs:** Structured rows appended to Google Sheets (configurable fields)

---

## What it does

Define your scrape job with a single JSON config in the **Input** node:
- `startUrl` — the first page to scrape
- `nextPageSelector` — CSS selector for the "Next page" link (enables auto-pagination)
- `fields` — array of `{ name, selector, value }` objects defining what to extract

The workflow then:
1. Fetches the start URL
2. Extracts all defined fields using CSS selectors
3. Checks for a next-page link — if found, loops back and repeats
4. Aggregates all results and appends them to Google Sheets

Great for: scraping product catalogues, blog archives, quote collections, competitor pages, job listings — any paginated site.

## Example Config

```json
{
  "startUrl": "https://quotes.toscrape.com/tag/humor/",
  "nextPageSelector": "li.next a[href]",
  "fields": [
    { "name": "author", "selector": "span > small.author", "value": "text" },
    { "name": "text",   "selector": "span.text",           "value": "text" }
  ]
}
```

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **Google Sheets** service account credential
3. Update the `Input` node JSON with your target URL, pagination selector, and fields
4. Update the `Store Scraped Data` node with your Google Sheet ID and tab
5. Click **Test workflow** — it runs once manually

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. Edit `workflow.py` to set your `START_URL`, `NEXT_PAGE_SELECTOR`, and `FIELDS`
4. `python workflow.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `START_URL` | First page to scrape |
| `NEXT_PAGE_SELECTOR` | CSS selector for the next-page link |
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key |
| `SPREADSHEET_ID` | Google Sheet to write results to |
| `SHEET_NAME` | Sheet tab name (default: `Sheet1`) |

## Known Issues / TODO

- **CSS selectors that return different counts per field produce empty cells** — if your `author` selector matches 10 elements but `text` only matches 8, rows 9 and 10 will have an empty `text` value. This is expected but can be confusing. Make sure your selectors target the same repeating container (e.g. a quote card), not individual elements at different depths.
- **Only works on static HTML** — if the site renders content via JavaScript, the scraper gets a blank page. No Playwright/Puppeteer integration yet. For JS-rendered sites, run the n8n version with a headless browser node or route through ScraperAPI.
- **No rate limiting beyond `DELAY_SECONDS`** — if you point this at a large site with hundreds of pages, a 1-second delay might still get you blocked or rate-limited. Some sites need randomised delays or session rotation.
- **`extractDomain()` in the n8n version** — this is a custom n8n expression that may not exist in older n8n instances (pre-1.x). If you get an expression error on the `Next Page Input` node, manually set the base URL as a string.

## Notes

- Works on static HTML pages. For JavaScript-rendered content, use the competitor-price-tracker (which leverages Bright Data) or add a headless browser step
- The `value` field in each field definition accepts `text`, `html`, or any HTML attribute name (e.g. `href`, `src`)
- The loop continues until no next-page link is found — make sure your selector is specific enough
