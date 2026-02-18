# Lead Enrichment & Router System

> Captures raw lead emails, enriches them with firmographic data, uses AI to score them, and routes them to Sales or Nurture sequences.

**Category:** Sales / Marketing Ops  
**Trigger:** Webhook (e.g., from a website form, Typeform, or Calendly)  
**Outputs:** 
- JSON payload containing structured enrichment data and an AI Lead Score (0-100).
- Triggers Slack alerts for Hot Leads (>80 score).
- Triggers an API call to ActiveCampaign/Mailchimp for Cold/Warm leads.

---

## What it does

When a raw email address is submitted (via top-of-funnel capture), this automation instantly pings the Clearbit API to find the associated company, industry, employee count, and the user's seniority. It then feeds this data into an LLM (OpenAI) to generate a "Lead Score". This allows the sales team to only talk to highly qualified leads, while lower-scoring leads are automatically pushed into a long-term email nurturing sequence without manual intervention.

## Inputs

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | The email address of the lead (passed as an argument) |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `score` | integer | 0-100 score of how qualified the lead is |
| `reason` | string | AI's justification for the score |
| `company_name` | string | Enriched company name |
| `industry` | string | Enriched industry |
| `seniority` | string | Enriched job level/seniority |
| `routing_dest` | string | Intended destination (`sales` or `nurture`) |

## Setup

### n8n
1. Import `workflow.json` into your n8n instance
2. Configure credentials: Set up the Slack API credential and generic HTTP credential (for your email marketing platform). 
3. Update the Execute Command node to aim at the correct `workflow.py` path.
4. Activate the workflow

### Python
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your Clearbit & OpenAI keys.
3. Run: `python workflow.py 'jane.doe@stripe.com'`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLEARBIT_API_KEY` | Your Clearbit Discovery/Enrichment key |
| `OPENAI_API_KEY` | Your OpenAI API key |

## Notes / Limitations

- **Clearbit Rate Limits:** Be careful here! Clearbit can get expensive fast. We've added a mock mode in the Python script if the key isn't found, so you don't burn credits while testing.
- **AI Hallucinations on Scoring:** The AI is instructed to return *only* JSON, but occasionally it might add backticks. The Python script strips these out via regex to prevent pipeline crashes.
