# ai-content-summariser

> Fetch any URL, extract the main content, and get a concise Markdown summary powered by OpenAI.

**Category:** AI  
**Trigger:** Webhook (HTTP POST with a URL) or Manual  
**Outputs:** Markdown summary saved to a file or returned via HTTP response

---

## What it does

Takes a URL as input (via a webhook payload or a command-line argument), fetches the page content, strips away boilerplate HTML, and sends the clean text to OpenAI's API to generate a structured Markdown summary.

Useful for: content research, competitive intelligence, briefings, newsletter curation, saving articles to Notion or Obsidian.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add your **OpenAI** credential (API key)
3. Optionally, connect the output to a "Write Binary File" or "Notion" node to save the summary
4. Send a POST request to the webhook URL with `{ "url": "https://example.com/article" }`

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. Run on a single URL:
   ```bash
   python workflow.py --url "https://example.com/article"
   ```
4. Or start as a local API server:
   ```bash
   python workflow.py --serve
   # POST to http://localhost:5001 with { "url": "..." }
   ```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o-mini`) |
| `OUTPUT_DIR` | Directory to save Markdown summaries (default: `./summaries`) |
| `PORT` | Port for the API server mode (default: `5001`) |

## Output format

```markdown
# [Article Title]

**Source:** https://...
**Summarised:** 2025-06-01

## Summary
...

## Key Points
- ...
- ...
```

## Notes

- Uses `trafilatura` for content extraction — handles most news sites and blog platforms well.
- Long articles are automatically truncated to stay within model token limits.
