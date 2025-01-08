"""
webhook-to-google-sheet

Starts a Flask webhook server. On receiving a POST request with a JSON
payload, appends all fields as a new row to the specified Google Sheet.

Usage:
    python workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    See .env.example
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
PORT = int(os.getenv("PORT", 5000))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

app = Flask(__name__)


def get_sheet():
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_JSON, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(SHEET_NAME)


def ensure_headers(sheet, keys):
    """If the sheet is empty, write headers from the payload keys."""
    existing = sheet.row_values(1)
    if not existing:
        sheet.append_row(["timestamp"] + list(keys))


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "No JSON payload received"}), 400

    sheet = get_sheet()
    ensure_headers(sheet, payload.keys())

    # Build row in the same order as headers (skip timestamp col)
    headers = sheet.row_values(1)
    row = [datetime.utcnow().isoformat()]
    for header in headers[1:]:  # skip "timestamp"
        row.append(payload.get(header, ""))

    sheet.append_row(row)
    print(f"✅ Appended row: {row}")
    return jsonify({"status": "ok", "row": row}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"}), 200


if __name__ == "__main__":
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID is not set. Check your .env file.")
    print(f"🚀 Webhook server running on http://0.0.0.0:{PORT}/webhook")
    app.run(host="0.0.0.0", port=PORT)
