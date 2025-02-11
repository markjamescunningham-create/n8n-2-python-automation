"""
news-aggregator

Pulls categorised news articles from NewsAPI, Mediastack, and CurrentsAPI,
normalises them into a consistent schema, and stores them (prints to stdout
by default; configure a database in .env for production use).

Usage:
    python workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    Copy .env.example → .env and fill in your values.
"""

import os
import json
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
NEWSAPI_KEY     = os.getenv("NEWSAPI_KEY", "")
MEDIASTACK_KEY  = os.getenv("MEDIASTACK_KEY", "")
CURRENTSAPI_KEY = os.getenv("CURRENTSAPI_KEY", "")

CATEGORIES     = os.getenv("CATEGORIES", "general,technology,business").split(",")
ARTICLE_LIMIT  = int(os.getenv("ARTICLE_LIMIT", "15"))
OUTPUT_FILE    = os.getenv("OUTPUT_FILE", "articles.json")


# ── Normalised schema ──────────────────────────────────────────────────────────
def make_article(title, summary, author, publisher, category, url,
                 content, image, publish_date, aggregator):
    return {
        "title": title or "",
        "summary": summary or "",
        "author": author or "",
        "publisher": publisher or "",
        "category": category or "",
        "sources": url or "",
        "content": content or "",
        "images": image or "",
        "publish_date": publish_date or "",
        "aggregator": aggregator,
        "status": "new",
    }


# ── NewsAPI ────────────────────────────────────────────────────────────────────
def fetch_newsapi_top_headlines():
    """Fetch top US headlines from NewsAPI."""
    if not NEWSAPI_KEY:
        print("[SKIP] NEWSAPI_KEY not set — skipping NewsAPI top headlines.")
        return []
    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize={ARTICLE_LIMIT}&apiKey={NEWSAPI_KEY}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    return [make_article(
        title=a.get("title"),
        summary=a.get("description"),
        author=a.get("author"),
        publisher=a.get("source", {}).get("name"),
        category="top-headlines",
        url=a.get("url"),
        content=a.get("content"),
        image=a.get("urlToImage"),
        publish_date=a.get("publishedAt"),
        aggregator="newsapi.org",
    ) for a in articles]


def fetch_newsapi_by_category(category: str):
    """Fetch NewsAPI articles for a specific category."""
    if not NEWSAPI_KEY:
        return []
    url = (f"https://newsapi.org/v2/top-headlines?"
           f"category={category}&pageSize={ARTICLE_LIMIT}&apiKey={NEWSAPI_KEY}")
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    return [make_article(
        title=a.get("title"),
        summary=a.get("description"),
        author=a.get("author"),
        publisher=a.get("source", {}).get("name"),
        category=category,
        url=a.get("url"),
        content=a.get("content"),
        image=a.get("urlToImage"),
        publish_date=a.get("publishedAt"),
        aggregator="newsapi.org",
    ) for a in articles]


# ── Mediastack ─────────────────────────────────────────────────────────────────
def fetch_mediastack(category: str):
    """Fetch articles from Mediastack for a specific category."""
    if not MEDIASTACK_KEY:
        print("[SKIP] MEDIASTACK_KEY not set — skipping Mediastack.")
        return []
    params = {
        "access_key": MEDIASTACK_KEY,
        "categories": category,
        "languages": "en",
        "sort": "published_desc",
        "limit": ARTICLE_LIMIT,
    }
    resp = requests.get("http://api.mediastack.com/v1/news", params=params, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("data", [])
    return [make_article(
        title=a.get("title"),
        summary=a.get("description"),
        author=a.get("author"),
        publisher=a.get("source"),
        category=a.get("category"),
        url=a.get("url"),
        content=a.get("description"),
        image=a.get("image"),
        publish_date=a.get("published_at"),
        aggregator="mediastack",
    ) for a in articles]


# ── CurrentsAPI ────────────────────────────────────────────────────────────────
def fetch_currentsapi():
    """Fetch latest news from CurrentsAPI."""
    if not CURRENTSAPI_KEY:
        print("[SKIP] CURRENTSAPI_KEY not set — skipping CurrentsAPI.")
        return []
    params = {
        "apiKey": CURRENTSAPI_KEY,
        "language": "en",
        "limit": ARTICLE_LIMIT,
    }
    resp = requests.get("https://api.currentsapi.services/v1/latest-news",
                        params=params, timeout=10)
    resp.raise_for_status()
    articles = resp.json().get("news", [])
    return [make_article(
        title=a.get("title"),
        summary=a.get("description"),
        author=a.get("author"),
        publisher=a.get("author"),
        category=", ".join(a.get("category", [])[:2]),
        url=a.get("url"),
        content=a.get("description"),
        image=a.get("image"),
        publish_date=a.get("published"),
        aggregator="currentsapi",
    ) for a in articles]


def main():
    all_articles = []

    # NewsAPI top headlines
    print("[→] Fetching NewsAPI top headlines...")
    all_articles += fetch_newsapi_top_headlines()

    # NewsAPI by category
    for cat in CATEGORIES:
        print(f"[→] Fetching NewsAPI category: {cat}...")
        all_articles += fetch_newsapi_by_category(cat.strip())

    # Mediastack by category
    for cat in CATEGORIES:
        print(f"[→] Fetching Mediastack category: {cat}...")
        all_articles += fetch_mediastack(cat.strip())

    # CurrentsAPI
    print("[→] Fetching CurrentsAPI latest news...")
    all_articles += fetch_currentsapi()

    print(f"\n[✓] Total articles collected: {len(all_articles)}")

    # Save to file (replace this with your DB write in production)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_articles, f, indent=2)
    print(f"[✓] Saved to {OUTPUT_FILE}")

    # Print a sample
    if all_articles:
        print("\nSample article:")
        print(json.dumps(all_articles[0], indent=2))


if __name__ == "__main__":
    main()
