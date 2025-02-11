# news-aggregator

> Pull categorised news articles from multiple sources (NewsAPI, Mediastack, CurrentsAPI) on a schedule and store them in a database for downstream use.

> **Status:** Working but has some rough edges — see Known Issues below.

**Category:** Tech / AI  
**Trigger:** Schedule (four independent schedules — one per API source)  
**Outputs:** Normalised article rows written to NocoDB (swappable for Google Sheets, Airtable, etc.)

---

## What it does

Runs four scheduled pipelines in parallel — one per news source:

| Source | Free tier | Schedule (default) |
|--------|-----------|-------------------|
| [CurrentsAPI](https://currentsapi.services) | 20 req/day | Daily at 06:10 |
| [MediaStack](https://mediastack.com) | 100 req/month | Every 2 days at 06:05 |
| [NewsAPI – Top Headlines](https://newsapi.org) | 100 req/day | Daily at 06:00 |
| [NewsAPI – Categories](https://newsapi.org) | 100 req/day | Daily at 06:01 |

Each pipeline:
1. Calls the respective API with configured categories and article limits
2. Normalises the response into a consistent schema: `title`, `summary`, `author`, `publisher`, `category`, `sources`, `content`, `images`, `publish_date`, `aggregator`
3. Writes each article to NocoDB (or your preferred database)

Configurable categories: `general`, `business`, `entertainment`, `health`, `science`, `sports`, `technology`

Great for: content pipelines, research agents, editorial queues, AI training datasets, marketing intelligence feeds.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add API keys in each HTTP Request node:
   - `call newsapi.org - Top Headlines` → add `apiKey` to URL
   - `call newsapi.org - categories` → add `apiKey` to URL
   - `call mediastack` → add `access_key` in JSON body
   - `call currentsapi` → add `apiKey` query param
3. Configure a **NocoDB API Token** credential — or replace NocoDB nodes with your preferred DB (Google Sheets, Airtable, Supabase)
4. Ensure your NocoDB table has these columns: `source_category`, `title`, `status`, `aggregator`, `publisher`, `summary`, `author`, `sources`, `content`, `images`, `publisher_date`
5. Enable all four Schedule Trigger nodes and activate

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`
3. `python workflow.py` — fetches from all four sources and prints/saves results

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NEWSAPI_KEY` | NewsAPI.org API key |
| `MEDIASTACK_KEY` | Mediastack API key |
| `CURRENTSAPI_KEY` | CurrentsAPI key |
| `NOCODB_URL` | NocoDB base URL (e.g. `https://your-cloud.nocodb.com`) |
| `NOCODB_TOKEN` | NocoDB API token |
| `NOCODB_TABLE_ID` | NocoDB table ID for articles |
| `CATEGORIES` | Comma-separated list of categories to fetch (default: `general,business,technology`) |
| `ARTICLE_LIMIT` | Max articles per API call (default: `15`) |

## Output Schema (per article)

```
source_category, title, summary, author, publisher,
sources (URL), content, images, publish_date, aggregator, status
```

## Known Issues / TODO

- **No deduplication** — if the same article appears in both NewsAPI top headlines and a category call (common for `technology`), it'll get inserted twice. Planning to add a title-hash check before writing.
- **Mediastack free plan math doesn't work across all 7 categories** — at 100 requests/month and 7 categories on a 2-day schedule, you'll hit ~15 calls/month, which is fine. But if you add more categories or shorten the schedule, you'll blow through the limit silently (no error, just stops returning results). Add monitoring.
- **No error handling if an API key works but returns 0 results** — the script will happily write an empty file. Worth adding a check.
- **NocoDB nodes in the n8n version need the correct API version** — NocoDB changed their API format between v1 and v2. The JSON here uses v3 node, which expects NocoDB v2 API. If you're on an older NocoDB instance this will break.

## Notes

- Mediastack free plan returns 100 calls/month — the 2-day schedule keeps you under limit across 7 categories
- NewsAPI free plan only returns headlines (no full article body) — `content` will be truncated at 200 chars
- To swap NocoDB for another database, replace each `Add * item` node with an equivalent "create row" operation — the Set nodes already normalise all fields
