"""
Voice to Notion Pipeline System

Takes an audio file, uses OpenAI Whisper to transcribe it, and uses
GPT-3.5-turbo to extract a clean Notion database record. Outputs the payload.

Usage:
    python workflow.py /path/to/downloaded_audio_file.ogg

Requirements:
    pip install -r requirements.txt

Environment variables:
    Copy .env.example → .env and fill in your values.
"""

import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file_path: str) -> str:
    """Uses OpenAI's Whisper model to convert audio to raw text."""
    if not OPENAI_API_KEY:
        # Note: Mock response for testing n8n pipeline without hitting an API or consuming tokens.
        return "Hey so I had this great idea for a new blog post, we should write about how n8n can totally replace Zapier for our enterprise clients because it's way cheaper."
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file '{file_path}' not found.")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    with open(file_path, "rb") as f:
        files = {
            "file": (os.path.basename(file_path), f, "audio/ogg"), 
        }
        data = {"model": "whisper-1"}
        
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

    return response.json().get("text", "")


def process_transcript_with_llm(transcript: str) -> dict:
    """Uses GPT-3.5 to clean, categorize, and extract structured fields."""
    if not OPENAI_API_KEY:
        return {
            "title": "Mock: n8n Enterprise Blog Post",
            "category": "Content Idea",
            "tags": ["blog", "n8n", "enterprise"],
            "content": "A blog post detailing how n8n is a cost-effective alternative to Zapier for enterprise clients.",
            "raw_transcript": transcript
        }

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a highly organized productivity assistant. You summarize scattered voice notes into clean, actionable records for a Notion database. Return ONLY a valid JSON object with these exact keys: 'title', 'category' (choose from: Content Idea, To-Do, Meeting Note, Random), 'tags' (array of 1-3 lowercase strings), and 'content' (a polished summary paragraph)."
            },
            {
                "role": "user",
                "content": f"Raw Voice Note: {transcript}"
            }
        ],
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()

    result_text = response.json()["choices"][0]["message"]["content"]
    
    # Strip any markdown backticks the LLM might hallucinate around the JSON.
    clean_text = re.sub(r"^```json\s*", "", result_text)
    clean_text = re.sub(r"```$", "", clean_text).strip()
    
    try:
        structured_data = json.loads(clean_text)
        # Always attach the raw transcript just in case the LLM misses an important detail!
        structured_data["raw_transcript"] = transcript
        return structured_data
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse LLM JSON output. Raw text was: {clean_text}")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing audio file argument. Usage: python workflow.py <path_to_audio_file>"}))
        sys.exit(1)
        
    audio_path = sys.argv[1].strip()
    
    try:
        raw_text = transcribe_audio(audio_path)
        final_payload = process_transcript_with_llm(raw_text)
        
        # This stringified JSON is passed to the n8n Notion node.
        print(json.dumps(final_payload, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
