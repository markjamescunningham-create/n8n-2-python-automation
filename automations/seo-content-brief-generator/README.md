# seo-content-brief-generator

> Given a target keyword, research the top SERP results via SerpAPI and use OpenAI to generate a structured content brief — recommended title, H2/H3 outline, word count target, secondary keywords, and topics to cover.

**Category:** Marketing / AI  
**Trigger:** Manual (CLI) or Webhook  
**Outputs:** Markdown brief saved to `briefs/` directory

---

## What it does

Closes the loop between your GSC/keyword-rank data (also in this repo) and actually writing content. Give it a keyword, and it:

1. Fetches the top N organic SERP results from SerpAPI
2. Passes the titles and snippets to OpenAI
3. Returns a full content brief: recommended title, meta description, word count target, H2/H3 outline, secondary keywords, key topics, and things to avoid

The brief is saved as a clean markdown file you can drop into Notion, Google Docs, or your CMS.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add your **SerpAPI** credential (HTTP Request node with API key header)
3. Add your **OpenAI** credential
4. Trigger manually via webhook or connect to a Google Sheets row trigger for batch processing
5. Update the `OUTPUT_DIR` variable if you want to write briefs somewhere other than the default

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. `python workflow.py --keyword "your target keyword"`
   - Or set `KEYWORD` in `.env` and just run `python workflow.py`

### Running tests (no API keys needed)
```bash
pip install -r requirements.txt
python -m pytest test_workflow.py -v
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SERPAPI_KEY` | SerpAPI key (serpapi.com — free plan: 100 searches/month) |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o-mini`) |
| `SERP_RESULTS` | Number of SERP results to analyse (default: `10`) |
| `KEYWORD` | Default keyword if not passed via CLI |
| `OUTPUT_DIR` | Directory for output briefs (default: `briefs/`) |

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `keyword` | string | Target keyword for the brief |

## Outputs

A markdown file in `OUTPUT_DIR/` containing:

| Field | Type | Description |
|-------|------|-------------|
| `recommended_title` | string | Suggested article title |
| `meta_description` | string | SEO meta description (≤160 chars) |
| `target_word_count` | int | Recommended article length |
| `primary_keyword` | string | Main keyword to target |
| `secondary_keywords` | list | Related keywords to include |
| `content_angle` | string | Unique angle to beat SERP competitors |
| `outline` | list | H2 sections with H3 subheadings |
| `key_topics_to_cover` | list | Topics the brief should address |
| `things_to_avoid` | list | Common competitor weaknesses to sidestep |

## Notes / Limitations

- SerpAPI free plan is 100 searches/month — enough for ad-hoc use; upgrade for bulk runs
- OpenAI costs are very low at `gpt-4o-mini` pricing (~$0.01–0.05 per brief); switch to `gpt-4o` for higher quality
- SERP results don't include page body content, only titles and snippets — the brief quality scales with how descriptive the snippets are
- Generated outlines are AI suggestions, not prescriptions — always review before sending to a writer
