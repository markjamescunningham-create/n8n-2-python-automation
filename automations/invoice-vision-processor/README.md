# Invoice Vision Processor System

> Monitors a mailbox for vendor invoices, uses Vision AI to extract line items and totals, and logs the data securely into Airtable.

**Category:** Operations / Finance  
**Trigger:** Email Inbox (e.g., Gmail trigger looking for `is:unread` with attachments)  
**Outputs:** 
- A JSON payload containing perfectly structured financial data (Vendor, Total, Date, Tax).
- Appends the data to an Airtable Base.
- Uploads the renamed PDF to a Google Drive archive.

---

## What it does

Manual data entry for receipts and invoices is a massive drain. This automation listens for new emails sent to `invoices@yourcompany.com`. n8n grabs the PDF attachment and passes it to this Python script. The script converts the PDF to an image and uses a multimodal LLM (like GPT-4o) to "look" at the invoice and extract the exact fields needed. The structured data is then pushed to Airtable, and the file is archived in Google Drive with a standardized naming convention. 

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | The local path to the downloaded PDF file (passed as an argument) |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `vendor` | string | Name of the supplier/vendor |
| `amount` | float | Total invoice amount |
| `date` | string | Invoice date (YYYY-MM-DD format) |
| `description` | string | A short summary of what the invoice is for |
| `confidence` | string | AI's self-assessed confidence on extraction ('high'/'low') |

## Setup

### n8n
1. Import `workflow.json` into your n8n instance.
2. Set up your Gmail/IMAP trigger credentials to look at a specific inbox/label.
3. Configure Airtable and Google Drive credentials securely.
4. Set the Execute Command node to pass the PDF binary data to the Python script.
5. Activate the workflow!

### Python
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your OpenAI key.
3. Run locally: `python workflow.py /path/to/test_invoice.pdf`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (for GPT-4o Vision extraction) |

## Notes / Limitations

- **Blurry Scans:** Vision AI works great on digitally exported PDFs, but can struggle on blurry photos of crumpled coffee receipts. If the AI is unsure, it sets `confidence` to `low`, allowing n8n to flag the row in Airtable for manual human review!
- **Library Dependency:** This script requires `PyMuPDF` to rasterize the PDF into an image for the API. Ensure your host environment (e.g., Docker container running n8n) has any necessary C-libraries for PDF rendering if you encounter build errors.
