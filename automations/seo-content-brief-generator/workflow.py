"""
seo-content-brief-generator

Takes a target keyword, fetches the top SERP results via SerpAPI,
extracts titles and headings structure, then uses OpenAI to generate
a structured content brief: recommended title, H2/H3 outline, word count
target, and key topics to cover.

Usage:
    python workflow.py --keyword "best CRM for startups"
    python workflow.py   # reads KEYWORD from .env

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import argparse
import json
import os
import re
import sys
from datetime import date

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
SERPAPI_KEY     = os.getenv("SERPAPI_KEY", "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SERP_RESULTS    = int(os.getenv("SERP_RESULTS", "10"))    # top N results to analyse
KEYWORD         = os.getenv("KEYWORD", "")
OUTPUT_DIR      = os.getenv("OUTPUT_DIR", "briefs")


# ── SERP research ──────────────────────────────────────────────────────────────
def fetch_serp_results(keyword: str) -> list[dict]:
    """Fetch top organic results from SerpAPI for the given keyword."""
    if not SERPAPI_KEY:
        print("[SKIP] SERPAPI_KEY not set — skipping SERP fetch.")
        return []

    params = {
        "engine":   "google",
        "q":        keyword,
        "num":      SERP_RESULTS,
        "api_key":  SERPAPI_KEY,
        "gl":       "us",
        "hl":       "en",
    }
    resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
    resp.raise_for_status()
    organic = resp.json().get("organic_results", [])

    return [
        {
            "position": r.get("position"),
            "title":    r.get("title", ""),
            "link":     r.get("link", ""),
            "snippet":  r.get("snippet", ""),
        }
        for r in organic[:SERP_RESULTS]
    ]


# ── Brief generation ───────────────────────────────────────────────────────────
def build_system_prompt() -> str:
    return (
        "You are an expert SEO content strategist. "
        "Given a target keyword and a list of top-ranking search results, "
        "produce a structured content brief in JSON. "
        "The JSON must follow this exact schema:\n"
        "{\n"
        '  "recommended_title": "string",\n'
        '  "meta_description": "string (max 160 chars)",\n'
        '  "target_word_count": integer,\n'
        '  "primary_keyword": "string",\n'
        '  "secondary_keywords": ["string"],\n'
        '  "content_angle": "string — what unique angle should this piece take?",\n'
        '  "outline": [\n'
        '    {"heading": "H2 text", "subheadings": ["H3 text", ...]},\n'
        "    ...\n"
        "  ],\n"
        '  "key_topics_to_cover": ["string"],\n'
        '  "things_to_avoid": ["string"]\n'
        "}\n"
        "Return only valid JSON, no markdown fences."
    )


def build_user_prompt(keyword: str, serp_results: list[dict]) -> str:
    serp_summary = "\n".join(
        f"{r['position']}. {r['title']}\n   {r['snippet']}"
        for r in serp_results
    )
    return (
        f"Target keyword: {keyword}\n\n"
        f"Top {len(serp_results)} SERP results:\n{serp_summary}\n\n"
        "Generate a content brief for a new article that should outrank these results."
    )


def generate_brief(keyword: str, serp_results: list[dict]) -> dict:
    """Call OpenAI to generate the content brief."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set. Check your .env file.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user",   "content": build_user_prompt(keyword, serp_results)},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


# ── Output ─────────────────────────────────────────────────────────────────────
def slug(text: str) -> str:
    """Convert a keyword to a filename-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def save_brief(keyword: str, brief: dict, serp_results: list[dict]) -> str:
    """Save the brief as a markdown file and return the path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{slug(keyword)}-{date.today().isoformat()}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    outline_md = ""
    for section in brief.get("outline", []):
        outline_md += f"\n## {section['heading']}\n"
        for sub in section.get("subheadings", []):
            outline_md += f"- ### {sub}\n"

    secondary = ", ".join(brief.get("secondary_keywords", []))
    topics    = "\n".join(f"- {t}" for t in brief.get("key_topics_to_cover", []))
    avoid     = "\n".join(f"- {a}" for a in brief.get("things_to_avoid", []))

    content = f"""# Content Brief: {brief.get('recommended_title', keyword)}

**Generated:** {date.today().isoformat()}  
**Primary keyword:** `{brief.get('primary_keyword', keyword)}`  
**Secondary keywords:** {secondary}  
**Target word count:** {brief.get('target_word_count', 'TBD')}  

## Meta description
> {brief.get('meta_description', '')}

## Content angle
{brief.get('content_angle', '')}

## Recommended outline
{outline_md}

## Key topics to cover
{topics}

## Things to avoid
{avoid}

---

## SERP research ({len(serp_results)} results analysed)

| # | Title | URL |
|---|-------|-----|
{"".join(f"| {r['position']} | {r['title']} | {r['link']} |\n" for r in serp_results)}
"""
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


# ── Main ───────────────────────────────────────────────────────────────────────
def main(keyword: str | None = None) -> dict:
    if keyword is None:
        keyword = KEYWORD
    if not keyword:
        raise ValueError("No keyword provided. Set KEYWORD in .env or pass --keyword.")

    print(f"[→] Keyword: {keyword}")
    print("[→] Fetching SERP results...")
    serp_results = fetch_serp_results(keyword)
    print(f"[✓] {len(serp_results)} result(s) retrieved.")

    print("[→] Generating content brief with OpenAI...")
    brief = generate_brief(keyword, serp_results)

    filepath = save_brief(keyword, brief, serp_results)
    print(f"[✓] Brief saved to: {filepath}")
    print(f"    Title:      {brief.get('recommended_title')}")
    print(f"    Word count: {brief.get('target_word_count')}")
    print(f"    Sections:   {len(brief.get('outline', []))}")

    return {"keyword": keyword, "brief": brief, "serp_results": serp_results, "output_file": filepath}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an SEO content brief.")
    parser.add_argument("--keyword", type=str, help="Target keyword (overrides KEYWORD in .env)")
    args = parser.parse_args()
    main(keyword=args.keyword)
