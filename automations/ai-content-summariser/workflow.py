"""
ai-content-summariser

Fetches the content of a URL, extracts the main article text using trafilatura,
and generates a structured Markdown summary using the OpenAI API.

Usage:
    # Summarise a single URL:
    python workflow.py --url "https://example.com/article"

    # Start as a local API server:
    python workflow.py --serve

    # POST to the server: { "url": "https://example.com/article" }

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
import trafilatura
from openai import OpenAI
from flask import Flask, request, jsonify

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./summaries")
PORT = int(os.getenv("PORT", 5001))
MAX_CHARS = 12000  # Truncate content to avoid exceeding token limits

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a research assistant. The user will provide the text of an article.
Return a structured Markdown summary in this exact format:

## Summary
A 2-4 sentence overview of the article.

## Key Points
- Bullet point 1
- Bullet point 2
- Bullet point 3
(Include 3-7 key points)

## Why It Matters
One sentence on the significance or takeaway.

Use plain Markdown only. Do not add any preamble or closing remarks."""


def fetch_content(url: str) -> str:
    """Download and extract the main text from a URL."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch URL: {url}")
    text = trafilatura.extract(downloaded)
    if not text:
        raise ValueError(f"Could not extract content from: {url}")
    return text[:MAX_CHARS]


def summarise(url: str, content: str) -> str:
    """Send content to OpenAI and get a Markdown summary."""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"URL: {url}\n\n---\n\n{content}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def save_summary(url: str, summary: str) -> str:
    """Save the summary to a Markdown file and return the file path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    slug = url.split("//")[-1].replace("/", "_").replace(".", "-")[:60]
    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date}_{slug}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w") as f:
        f.write(f"# Summary\n\n")
        f.write(f"**Source:** {url}\n")
        f.write(f"**Summarised:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(summary)

    return filepath


def process_url(url: str) -> dict:
    print(f"🔍 Fetching: {url}")
    content = fetch_content(url)
    print(f"📝 Summarising ({len(content)} chars) with {OPENAI_MODEL}...")
    summary = summarise(url, content)
    filepath = save_summary(url, summary)
    print(f"✅ Summary saved to: {filepath}")
    return {"url": url, "summary": summary, "saved_to": filepath}


# ── Flask API server mode ─────────────────────────────────────────────────────

@app.route("/", methods=["POST"])
def api_summarise():
    payload = request.get_json(force=True)
    url = payload.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' in request body"}), 400
    try:
        result = process_url(url)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "model": OPENAI_MODEL}), 200


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY is not set. Check your .env file.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Summarise a URL with OpenAI")
    parser.add_argument("--url", help="URL to summarise")
    parser.add_argument("--serve", action="store_true", help="Start as a local API server")
    args = parser.parse_args()

    if args.serve:
        print(f"🚀 API server running on http://0.0.0.0:{PORT}")
        app.run(host="0.0.0.0", port=PORT)
    elif args.url:
        process_url(args.url)
    else:
        parser.print_help()
