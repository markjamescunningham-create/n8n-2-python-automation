# scheduled-email-from-sheets

> Read a Google Sheet of scheduled emails and automatically send each one via Gmail on its target date.

**Category:** Marketing  
**Trigger:** Schedule (every minute — polls for today's pending emails)  
**Outputs:** Gmail emails sent, Google Sheet status updated to "Sent successfully"

---

## What it does

Reads a Google Sheet containing a list of emails to send (with Name, Email, Title, Subject, Date, Status). Every minute, it filters for rows where:
- Status = `Waiting for sending`
- Date matches today (format: `yyyy/MM/dd`)
- All required fields are present

For each matching row, it sends a Gmail message and updates the row status to `Sent successfully`.

Great for: scheduled customer outreach, drip campaigns managed in a spreadsheet, birthday/anniversary emails, event reminders.

## Google Sheet Template

Copy this template to get started:  
[Sending Messages to Customers](https://docs.google.com/spreadsheets/d/1efCCzfeUX0AETz2wsULQN90OBCOKK-gBoDaptzcBHdE/edit?usp=sharing)

**Required columns:** `ID`, `Name`, `Email`, `Date` (yyyy/MM/dd), `Title`, `Subject`, `Status`

## Setup

### n8n
1. Import `workflow.json` into n8n
2. Add **Google Sheets** OAuth2 credential
3. Add **Gmail** OAuth2 credential
4. Update the `documentId` in both Google Sheets nodes to point to your sheet
5. Activate — it will run every minute and process today's pending rows

### Python
1. `pip install -r requirements.txt`
2. Create a Google service account, download JSON key, share your sheet with the service account
3. Set up Gmail sending via `smtplib` with an App Password (or Google API)
4. Copy `.env.example` → `.env` and fill in your values
5. `python workflow.py` — run once manually, or schedule with cron

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CREDENTIALS_JSON` | Path to Google service account key file |
| `SPREADSHEET_ID` | Your Google Sheet ID |
| `SHEET_NAME` | Sheet tab name (default: `Sheet1`) |
| `GMAIL_ADDRESS` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your main password) |

## Notes

- Date format in the sheet must be `yyyy/MM/dd` (e.g. `2025/06/15`)
- The script checks the `Status` column and skips rows that aren't `Waiting for sending`
- After sending, the script updates the row status to `Sent successfully`
