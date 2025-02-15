# b2b-lead-researcher

> Automatically scrape a list of company websites (profile pages and news/changelog pages), analyse the content with AI, and store structured CRM-ready records in Airtable — updating Google Sheets as a staging database along the way.

**Category:** AI / Tech  
**Trigger:** Manual  
**Outputs:** Airtable records with company persona, strategic focus, recent activities, and a 1-sentence executive summary

---

## What it does

Reads a list of target company URLs from Google Sheets, then for each URL:

1. **Scrapes** the page using BrowserAct (bypasses bot detection, handles JS rendering)
2. **Analyses** the raw scraped JSON with an AI agent (GPT-5 via OpenRouter), detecting whether it's a "News/Changelog" or "Company Profile" page and extracting:
   - `data_type`, `company_name`, `primary_date`, `core_summary`, `key_entities`, `strategic_focus`, `raw_content_snippet`, `source_url`
3. **Stores** the structured data back to Google Sheets (staging)
4. After all URLs are scraped, **synthesises** all the page data for a company into a single Airtable record with:
   - **Notes** (Markdown): Company Persona, Strategic Focus, Recent Activities, Key Tech
   - **Attachment Summary**: 1-sentence executive bio

Great for: B2B sales prospecting, competitive intelligence, agency new business research, investor due diligence.

## Requirements

- **[BrowserAct](https://browseract.com)** account — use the "B2B Contact Research" template
- **[OpenRouter](https://openrouter.ai)** API key (uses GPT-5 and Gemini Flash)
- **Google Sheets** with a column `Page URL` (one company page URL per row — can be multiple pages per company)
- **Airtable** base with columns: `Name`, `Notes`, `Status`, `Attachments`, `Attachment Summary`

## Google Sheet Structure

```
| Page URL                                  |
|-------------------------------------------|
| https://ghost.org/changelog/              |
| https://ghost.org/about/                  |
| https://anothercompany.com/news/          |
```

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **BrowserAct** API credential — set Workflow ID to your "B2B Contact Research" template ID
3. Add **OpenRouter** credential (GPT-5 for analysis, Gemini Flash for synthesis)
4. Add **Google Sheets** OAuth credential — update both Sheets nodes with your Sheet ID
5. Add **Airtable** credential — update the `Create a record` node with your base and table IDs
6. Click **Manual execution**

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`
3. Add your target URLs to `targets.csv` (one per line)
4. `python workflow.py`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Chat model (default: `openai/gpt-4o`) |
| `AIRTABLE_TOKEN` | Airtable personal access token |
| `AIRTABLE_BASE_ID` | Airtable base ID |
| `AIRTABLE_TABLE_ID` | Airtable table ID |
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key |
| `SPREADSHEET_ID` | Google Sheet ID (staging database) |
| `TARGETS_CSV` | Path to CSV file with `Page URL` column |

## Notes

- The Python version uses `requests` + `BeautifulSoup` for scraping instead of BrowserAct — works for most static pages but may miss JS-rendered content
- Add multiple page types per company (about, news, pricing) to give the AI synthesiser richer context for the Airtable record
- The `Airtable Notes` field uses Markdown formatting — enable "Rich text" on that field in Airtable
