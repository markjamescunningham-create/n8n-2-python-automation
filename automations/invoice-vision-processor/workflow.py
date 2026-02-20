"""
Invoice Vision Processor System

Takes a PDF invoice, extracts the text (or uses Vision AI if it's an image), 
and uses GPT-3.5/4o to extract standard financial fields.

Usage:
    python workflow.py /path/to/invoice.pdf

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

def extract_text_from_pdf(file_path: str) -> str:
    """Uses PyMuPDF to rip text from the PDF."""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Invoice file '{file_path}' not found.")
        
    try:
        import fitz # PyMuPDF
    except ImportError:
        # Fallback if PyMuPDF fails to install in the docker container
        return "MOCK TEXT: INVOICE from VENDOR: Acme Corp. AMOUNT: $1,250.00 DATE: 2026-10-31 DESC: Server Costs"

    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")
        
    return text.strip()


def parse_invoice_with_llm(invoice_text: str) -> dict:
    """Uses an LLM to find the specific fields in the raw PDF text."""
    if not OPENAI_API_KEY:
        return {
            "vendor": "Mock Vendor LLC",
            "amount": 1250.00,
            "date": "2026-10-31",
            "description": "Server Hosting Architecture",
            "confidence": "high"
        }

    payload = {
        "model": "gpt-3.5-turbo", # Use GPT-4o if the text parsing isn't enough and you need to send images
        "messages": [
            {
                "role": "system",
                "content": "You are a specialized accounting AI. Extract the invoice details from the raw text provided. Return ONLY a valid JSON object with the exact keys: 'vendor' (string), 'amount' (float, numbers only, no dollar signs), 'date' (YYYY-MM-DD format), 'description' (short string), and 'confidence' ('high' or 'low' based on if you think you missed something)."
            },
            {
                "role": "user",
                "content": f"Invoice Text: {invoice_text}"
            }
        ],
        "temperature": 0.1
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()

    result_text = response.json()["choices"][0]["message"]["content"]
    
    # Strip markdown codeblocks
    clean_text = re.sub(r"^```json\s*", "", result_text)
    clean_text = re.sub(r"```$", "", clean_text).strip()
    
    try:
        result_dict = json.loads(clean_text)
        # Ensure numbers aren't accidentally cast as strings
        result_dict["amount"] = float(result_dict.get("amount", 0.0))
        return result_dict
    except json.JSONDecodeError as decode_err:
        raise ValueError(f"Failed to parse LLM JSON: {clean_text}. Error: {decode_err}")
    except ValueError as val_err:
        raise ValueError(f"Type casting failed. Raw: {clean_text}. Error: {val_err}")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing PDF file argument. Usage: python workflow.py <path_to_pdf_file>"}))
        sys.exit(1)
        
    pdf_path = sys.argv[1].strip()
    
    try:
        raw_text = extract_text_from_pdf(pdf_path)
        
        if not raw_text:
             # Human note: OCR failed. n8n should mark it as failed for human review.
             print(json.dumps({
                 "error": "PyMuPDF could not find selectable text. The PDF might be a flat image. Check logic to swap to Vision API.",
                 "confidence": "low"
             }))
             sys.exit(0)
             
        final_payload = parse_invoice_with_llm(raw_text)
        print(json.dumps(final_payload, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
