# webhook-to-google-sheet

> Receive a webhook payload and append a row to a Google Sheet — instantly.

**Category:** General  
**Trigger:** Webhook (HTTP POST)  
**Outputs:** New row appended to a Google Sheet

---

## What it does

Listens for an incoming HTTP POST request (e.g. from a form, another app, or any service that sends webhooks). Extracts the payload fields and appends them as a new row in a specified Google Sheet.

Great for: form submissions, lead capture, event logging, CRM-lite setups.

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add your **Google Sheets** credential (OAuth2)
3. Update the **Spreadsheet ID** and **Sheet Name** in the "Google Sheets" node
4. Copy the webhook URL from the "Webhook" node and use it in your source app
5. Activate the workflow

### Python
1. `pip install -r requirements.txt`
2. Create a Google Cloud service account, download the JSON key
3. Share your Google Sheet with the service account email
4. Copy `.env.example` → `.env` and fill in your values
5. `python workflow.py` — starts a local Flask server on port 5000

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CREDENTIALS_JSON` | Path to your Google service account JSON key file |
| `SPREADSHEET_ID` | The ID from your Google Sheet URL |
| `SHEET_NAME` | Name of the sheet tab (e.g. `Sheet1`) |
| `PORT` | Port for the Flask server (default: `5000`) |

## Notes

- The Python script appends **all keys** from the JSON payload as columns. If your sheet has headers, make sure they match the payload keys.
- For production use, add authentication to the webhook endpoint (e.g. a shared secret header).
