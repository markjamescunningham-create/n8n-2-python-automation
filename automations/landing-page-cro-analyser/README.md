# landing-page-cro-analyser

> Submit a landing page URL and get an AI-powered roast + 10 specific Conversion Rate Optimisation recommendations.

**Category:** AI / Marketing  
**Trigger:** n8n Form (browser form submission)  
**Outputs:** Detailed CRO analysis returned in the browser

---

## What it does

Presents a web form where a user enters a landing page URL. The workflow then:
1. Scrapes the landing page HTML
2. Passes the content to an OpenAI agent (using `o1` reasoning model)
3. Returns a structured response with:
   - A candid, human-style **roast** of the page
   - **10 highly specific CRO recommendations** tailored to that exact page

Each recommendation goes beyond generic advice (e.g. "add a CTA") — it provides the actual copy, layout, or psychology change to implement.

Great for: founders reviewing their own pages, agencies auditing client sites, marketers before launching a campaign.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **OpenAI** credential (API key)
3. The form trigger creates a URL automatically — share that URL with users
4. Activate the workflow
5. Open the form URL and enter any landing page URL

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. Analyse a URL:
   ```bash
   python workflow.py --url "https://example.com/landing"
   ```
4. Or serve as a local API:
   ```bash
   python workflow.py --serve
   # POST to http://localhost:5002 with { "url": "..." }
   ```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | Model to use (default: `o1` — falls back to `gpt-4o` if unavailable) |
| `PORT` | Port for server mode (default: `5002`) |

## Output Format

```
## Roast
[Candid, human-style critique of the page's weaknesses]

## 10 CRO Recommendations
1. [Specific recommendation with exact copy/change]
2. ...
```

## Notes

- Uses `o1` (reasoning model) by default for deeper analysis — this is slower but produces significantly better output than GPT-4o for analytical tasks
- Page content is extracted via HTTP request and HTML stripping — works on most static pages, but may not capture JS-rendered content
- For JS-heavy pages, consider adding a headless browser step (e.g. Playwright)
