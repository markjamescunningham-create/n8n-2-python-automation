"""
rss-to-slack

Polls a list of RSS feeds and posts new items to a Slack channel.
Tracks seen items in a local JSON file to avoid duplicates.
Skips items older than 24 hours on first run.

Usage:
    python workflow.py

Schedule with cron (e.g. every hour):
    0 * * * * /usr/bin/python3 /path/to/workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import feedparser
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#general")
RSS_FEED_URLS = [url.strip() for url in os.getenv("RSS_FEED_URLS", "").split(",") if url.strip()]
STATE_FILE = os.getenv("STATE_FILE", "seen_items.json")
SKIP_OLDER_THAN_HOURS = 24  # On first run, skip items older than this


def load_seen_items() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_items(seen: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


def parse_entry_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def post_to_slack(client: WebClient, item_title: str, item_link: str, feed_title: str):
    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=f"*{feed_title}*\n<{item_link}|{item_title}>",
            unfurl_links=True,
        )
        print(f"  ✅ Posted: {item_title}")
    except SlackApiError as e:
        print(f"  ❌ Slack error: {e.response['error']}")


def main():
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN is not set. Check your .env file.")
    if not RSS_FEED_URLS:
        raise ValueError("RSS_FEED_URLS is not set. Check your .env file.")

    client = WebClient(token=SLACK_BOT_TOKEN)
    seen = load_seen_items()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SKIP_OLDER_THAN_HOURS)
    new_seen = set()
    posted = 0

    for feed_url in RSS_FEED_URLS:
        print(f"\n📡 Checking feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        feed_title = feed.feed.get("title", feed_url)

        for entry in feed.entries:
            uid = entry.get("id") or entry.get("link", "")
            if not uid:
                continue

            new_seen.add(uid)

            if uid in seen:
                continue

            pub_date = parse_entry_date(entry)
            if pub_date and pub_date < cutoff:
                print(f"  ⏭  Skipping old item: {entry.get('title', uid)}")
                continue

            print(f"  📰 New item: {entry.get('title', uid)}")
            post_to_slack(client, entry.get("title", "No title"), entry.get("link", ""), feed_title)
            posted += 1
            time.sleep(0.5)  # Avoid Slack rate limits

    seen.update(new_seen)
    save_seen_items(seen)
    print(f"\n✅ Done. Posted {posted} new item(s).")


if __name__ == "__main__":
    main()
