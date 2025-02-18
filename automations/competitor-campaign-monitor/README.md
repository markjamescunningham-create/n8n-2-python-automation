# competitor-campaign-monitor

> Scrape a list of competitor landing pages weekly, compare current content against the previous snapshot, detect pricing and messaging changes, and post an AI-written intelligence report directly to Slack.

> **Status:** Works for static pages out of the box. JS-rendered sites (most SaaS pricing pages) need BrowserAct — see notes.

**Category:** Marketing / Tech  
**Trigger:** Schedule (weekly — configurable)  
**Outputs:** Slack digest reporting changed pages with severity, verdict, and strategic analysis

---

## What it does

1. **Reads** a list of competitor URLs from Google Sheets
2. **Scrapes** each page using BrowserAct (handles JS, bypasses bot detection)
3. **Analyses** current vs. previous data using an AI agent (GPT-5 via OpenRouter):
   - Detects price changes (direction + amount)
   - Detects content/offer changes (bundle items, banner copy, messaging)
   - Assigns a severity: `None`, `Low`, or `High`
   - Writes a strategic verdict ("Aggressive push on bundle pricing before Q2")
4. **Stores** updated data back to Google Sheets (the new snapshot becomes the baseline for next run)
5. **Generates** a Slack-formatted report across all changed pages
6. **Posts** each message to your designated Slack channel

**Change severity:**
- 🔴 **High** — Price changed or major content shift
- 🟡 **Low** — Minor copy or description update
- 🟢 **New** — First time tracking this page

Great for: e-commerce teams tracking competitor pricing, growth marketers monitoring rival campaigns, agencies reporting on client competitors, SaaS teams tracking landing page iterations.

## Requirements

- **[BrowserAct](https://browseract.com)** — use the "Competitor Campaign Monitoring" template
- **[OpenRouter](https://openrouter.ai)** API key (GPT-5)
- **Google Sheets** with columns: `Page URL`, `Page Context`, `Comparison Analysis`
- **Slack** workspace with a channel for the report

## Google Sheet Structure

```
| Page URL                          | Page Context | Comparison Analysis |
|-----------------------------------|--------------|---------------------|
| https://competitor.com/pricing    |              |                     |
| https://competitor.com/bundle     |              |                     |
```

Columns 2 and 3 are written automatically by the workflow after each run.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **BrowserAct** credential — set Workflow ID to your "Competitor Campaign Monitoring" template ID
3. Add **OpenRouter** credential
4. Add **Google Sheets** OAuth credential — update all Sheets nodes with your Sheet ID
5. Add **Slack** credential — update the `Send a message` node with your channel ID
6. Set your preferred schedule (default: weekly)
7. Activate

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`
3. Add target URLs to `targets.csv`
4. `python workflow.py` — runs once, compares against `previous_data.json` (auto-created on first run)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Model (default: `openai/gpt-4o`) |
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key |
| `SPREADSHEET_ID` | Google Sheet ID (URL list + snapshot storage) |
| `SLACK_BOT_TOKEN` | Slack bot token |
| `SLACK_CHANNEL_ID` | Slack channel ID to post reports to |
| `TARGETS_CSV` | Path to CSV with `Page URL` column |

## Known Issues / TODO

- **Scraper only reads the first 5000 chars of page text** — pricing info is often buried lower in the page (especially on long-form pricing pages with feature tables). The 5000-char limit means it can miss actual prices entirely and just compare hero copy. Thinking about bumping this or doing a targeted extraction of `$` patterns first.
- **Price detection is naive** — `scrape_page()` grabs any string containing `$`, which on some pages returns dozens of strings from unrelated elements (testimonials quoting dollar amounts, currency disclaimers, etc.). Not all of them are product prices. TODO: tighten the selector.
- **The n8n workflow JSON uses a plain HTTP Request** rather than BrowserAct — the original workflow uses BrowserAct for JS rendering but that requires a paid account. The JSON here is a functional fallback that works for static sites. If your target sites are built on React/Next.js, add the BrowserAct node.
- **Snapshot file in Python version is just a local JSON** — fine for running locally, not great if you move this to a server or cloud function. Should swap for a proper store (Sheets, Redis, etc.) eventually.

## Notes

- The first run will store a baseline snapshot — meaningful comparisons start from the second run onwards
- For JS-heavy pages (React/Next.js storefronts), BrowserAct is essential — the Python version falls back to `requests` + `BeautifulSoup` which may miss dynamically loaded content
- To monitor multiple competitors, use separate Sheet tabs or separate workflow instances with different URL lists
- Add a **filter** before the Slack node to only send alerts for `High` severity changes if you want less noise
