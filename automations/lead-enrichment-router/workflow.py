"""
Lead Enrichment Router System

Grabs a raw email, enriches it via Clearbit, and asks OpenAI to score it (0-100).
Outputs a clean JSON payload for n8n to route perfectly.

Usage:
    python workflow.py 'test@stripe.com'

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
CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def fetch_clearbit_data(email: str) -> dict:
    """Enriches the email address using Clearbit's API."""
    if not CLEARBIT_API_KEY:
        # Note: Added a fallback mock so we don't crash while testing n8n nodes locally
        # or if the user burns through their Clearbit limit.
        return {
            "company_name": "TestCorp",
            "industry": "Software",
            "seniority": "Executive",
            "company_size": "50-250",
            "mocked": True
        }

    url = f"https://person.clearbit.com/v2/combined/find?email={email}"
    headers = {"Authorization": f"Bearer {CLEARBIT_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        person = data.get("person", {})
        company = data.get("company", {})
        
        return {
            "company_name": company.get("name", "Unknown"),
            "industry": company.get("category", {}).get("sector", "Unknown"),
            "seniority": person.get("employment", {}).get("role", "Unknown"),
            "company_size": company.get("metrics", {}).get("employees", "Unknown"),
            "mocked": False
        }
    except requests.exceptions.HTTPError as e:
        # 404 just means no data found for this email, which is common.
        if e.response.status_code == 404:
            return {
                "company_name": "Unknown",
                "industry": "Unknown",
                "seniority": "Unknown",
                "company_size": "Unknown",
                "mocked": False
            }
        raise


def score_lead_with_ai(email: str, enriched_data: dict) -> dict:
    """Uses OpenAI to evaluate how 'hot' the lead is based on enriched data."""
    if not OPENAI_API_KEY:
        return {
            "score": 50,
            "reason": "OpenAI API key missing - fallback score applied.",
            "routing_dest": "nurture"
        }

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a b2b sales executive. Score this inbound lead from 0 to 100 based on their company size, industry, and role. 'Hot' leads (decision-makers at tech/software companies) should score 80+. Return ONLY a raw JSON object like: {\"score\": 85, \"reason\": \"Executive at large tech firm\"}"
            },
            {
                "role": "user",
                "content": f"Email: {email}\nEnriched Data: {json.dumps(enriched_data)}"
            }
        ],
        "temperature": 0.2
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()
    
    result_text = response.json()["choices"][0]["message"]["content"]
    
    # Clean up formatting (AI sometimes ignores 'ONLY RETURN JSON')
    clean_text = re.sub(r"^```json\s*", "", result_text)
    clean_text = re.sub(r"```$", "", clean_text).strip()
    
    score_data = json.loads(clean_text)
    score_data["routing_dest"] = "sales" if int(score_data.get("score", 0)) >= 80 else "nurture"
    
    return score_data


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing email argument. Usage: python workflow.py <email>"}))
        sys.exit(1)
        
    target_email = sys.argv[1].strip()
    
    try:
        enriched = fetch_clearbit_data(target_email)
        ai_evaluation = score_lead_with_ai(target_email, enriched)
        
        # Merge the dicts for the final n8n payload
        final_payload = {
            "email": target_email,
            **enriched,
            **ai_evaluation
        }
        
        # This print statement is what n8n actually reads!
        print(json.dumps(final_payload, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
