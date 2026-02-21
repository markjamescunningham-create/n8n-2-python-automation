# meeting-action-extractor

> Paste in a meeting transcript, get back a structured list of action items — owner, task, due date, and priority — saved to CSV and optionally Notion.

**Category:** AI / General  
**Trigger:** Manual (CLI), Webhook, or Scheduled (with transcript input)  
**Outputs:** `action_items.csv` + optional Notion database pages

---

## What it does

You give it a transcript (copy-pasted from Zoom, Otter.ai, Google Meet, etc.) and it uses OpenAI to extract every action item mentioned, structured as:

| Field | Description |
|-------|-------------|
| `owner` | Who's responsible |
| `task` | What needs to be done |
| `due_date` | When it's due (if mentioned) |
| `priority` | High / Medium / Low |
| `context` | One-sentence quote of context from the transcript |

Results are appended to a running CSV and optionally pushed to a Notion database as individual task pages.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Set your **OpenAI** credential
3. Optionally add your **Notion** credential and target database ID
4. Trigger via webhook: POST `/webhook/meeting-actions` with body `{"transcript": "..."}`

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. Run one of:
   ```bash
   python workflow.py --transcript meeting.txt
   cat meeting.txt | python workflow.py
   ```

### Running tests (no API keys needed)
```bash
pip install -r requirements.txt
python -m pytest test_workflow.py -v
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model (default: `gpt-4o-mini`) |
| `TRANSCRIPT_FILE` | Default transcript path (if not using CLI flag or stdin) |
| `OUTPUT_CSV` | CSV file to append results to (default: `action_items.csv`) |
| `NOTION_API_KEY` | Notion integration token (optional) |
| `NOTION_DB_ID` | Notion database ID to write task pages to (optional) |

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `transcript` | string | Raw meeting transcript text |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | Person responsible for the action |
| `task` | string | What needs to be done |
| `due_date` | string \| null | ISO 8601 date, or null if not mentioned |
| `priority` | string | High / Medium / Low |
| `context` | string | One-sentence context from transcript |
| `extracted_at` | string | UTC timestamp of extraction |

## Notes / Limitations

- Works best with verbatim transcripts; summarised notes may miss implicit tasks
- `gpt-4o-mini` is accurate enough for most action item extraction; use `gpt-4o` for complex or ambiguous transcripts
- Notion property types must match: the database needs `Name` (title), `Owner` (text), `Due Date` (date), `Priority` (select with options High/Medium/Low), `Context` (text) — create these before activating
- The script **appends** to the CSV on each run — useful for building a running log; filter by `extracted_at` to isolate a specific meeting
