# Voice to Notion Pipeline

> Turns rambling voice notes (from WhatsApp/Telegram) into clean, structured tasks or ideas in a Notion Database.

**Category:** Productivity / Marketing Ops  
**Trigger:** Messaging App Bot (e.g., Telegram, WhatsApp)  
**Outputs:** 
- A formatted record inserted into a Notion database table, categorized and tagged.

---

## What it does

Great ideas often happen away from the keyboard. This automation lets you send a voice memo to a private bot on your phone. n8n catches the audio, passes it to this Python script (which uses OpenAI's Whisper model to transcribe it accurately), and then uses an LLM to extract the core idea, title, category, and tags. The structured JSON is then pushed seamlessly into your Notion database.

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | The local path to the downloaded audio file (passed as an argument) |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | A concise, descriptive title for the idea |
| `category` | string | Classification (e.g., 'Content Idea', 'To-Do', 'Meeting Note') |
| `tags` | list | Relevant tags extracted from context |
| `content` | string | The cleaned up, structured summary of the voice note |
| `raw_transcript` | string | The original Whisper transcription (just in case) |

## Setup

### n8n
1. Import `workflow.json` into your n8n instance.
2. Set up your Telegram Bot / WhatsApp trigger credentials.
3. Set up your Notion API credentials and select the target database.
4. Update the Execute Command node to aim at the correct `workflow.py` path and file variable.
5. Activate the workflow!

### Python
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your OpenAI key.
3. Run locally: `python workflow.py /path/to/test_audio.ogg`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (used for Whisper & text structuring) |
| `NOTION_DATABASE_ID` | (Used directly in n8n) The UUID of your Notion list/board |

## Notes / Limitations

- **Hallucinations:** Whisper is incredible, but if there's heavy wind/noise, it might occasionally hallucinate a phrase. We save the `raw_transcript` in the Notion page just in case the AI summary misses crucial context.
- **Audio Formats:** This script expects standard compressed web-audio (like `.ogg` from Telegram or `.m4a` from iOS). If n8n downloads a weird proprietary format, you may need an FFmpeg conversion node first before running this script.
