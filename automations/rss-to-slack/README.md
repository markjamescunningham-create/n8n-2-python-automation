# rss-to-slack

> Monitor one or more RSS feeds and automatically post new items to a Slack channel.

**Category:** Marketing  
**Trigger:** Schedule (runs on a cron — default: every hour)  
**Outputs:** Slack message for each new RSS item

---

## What it does

Polls a list of RSS feeds on a schedule. For each new item (not previously seen), sends a formatted message to a specified Slack channel with the title, link, and source.

Great for: keeping your team updated on competitor news, industry publications, product updates, or content inspiration.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add your **Slack** credential (OAuth2 or Bot Token)
3. Update the **RSS Feed URL** in the "RSS Read" node
4. Set your **Slack channel** in the "Slack" node
5. Adjust the cron schedule if needed (default: every hour)
6. Activate the workflow

### Python
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your values
3. `python workflow.py` — runs once immediately; use cron or a scheduler (e.g. `crontab -e`) to run on a schedule

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Slack bot token (starts with `xoxb-`) |
| `SLACK_CHANNEL` | Channel ID or name (e.g. `#content-feed`) |
| `RSS_FEED_URLS` | Comma-separated list of RSS feed URLs |
| `STATE_FILE` | Path to a JSON file used to track seen items (default: `seen_items.json`) |

## Notes

- Seen items are tracked by GUID/link in a local `seen_items.json` file. On first run, all existing items will be posted.
- To avoid the first-run flood, the script skips items older than 24 hours by default.
