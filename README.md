# n8n Automation Library

I spend a lot of time in n8n and Python building automations for marketing and ops work — things that used to take me (or my clients) hours every week. This repo is where I keep the ones worth keeping.

Everything here is dual-format: an **n8n workflow JSON** you can import and run in minutes, and an equivalent **Python script** for people who'd rather just run a file. Both do the same job.

No grand ambitions here. Just a place to stop rebuilding the same stuff from scratch.

---

## What's in here

Mostly things I've actually needed:

- Pulling data out of Google Search Console without clicking through the UI every morning
- Sending emails from a spreadsheet on a schedule (embarrassingly useful)
- Tracking whether competitor pricing pages have changed
- Getting AI to tell me which Facebook ads to kill before I spend more money on them

Some of these are polished. Some are still rough around the edges — I've noted those where relevant.

---

## 📂 Structure

```
automations/
└── <automation-name>/
    ├── README.md        # What it does, setup, known issues
    ├── workflow.json    # n8n export — import directly
    ├── workflow.py      # Python equivalent
    ├── .env.example     # Environment variable template
    └── requirements.txt

templates/
└── automation-template/  # Boilerplate for new additions
```

---

## 🚀 How to run these

### n8n
1. Open your n8n instance
2. **Import workflow** → select the `workflow.json`
3. Follow the setup steps in the automation's `README.md`
4. Activate

### Python
```bash
cd automations/<automation-name>
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python workflow.py
```

---

## ⚡ Automations

| Name | Category | Description |
|------|----------|-------------|
| [webhook-to-google-sheet](automations/webhook-to-google-sheet/) | General | Capture webhook payloads and append rows to Google Sheets |
| [rss-to-slack](automations/rss-to-slack/) | Marketing | Monitor RSS feeds and post new items to Slack |
| [ai-content-summariser](automations/ai-content-summariser/) | AI | Summarise any URL with OpenAI, output Markdown |
| [scheduled-email-from-sheets](automations/scheduled-email-from-sheets/) | Marketing | Read a Google Sheet and send emails on their target date |
| [search-console-to-sheets](automations/search-console-to-sheets/) | Marketing | Pull GSC keyword/page data to Sheets on a schedule |
| [landing-page-cro-analyser](automations/landing-page-cro-analyser/) | AI / Marketing | Submit a URL, get AI-powered CRO recommendations |
| [keyword-rank-tracker](automations/keyword-rank-tracker/) | Marketing | Track top 5 SERP results for keywords, log to Sheets |
| [competitor-price-tracker](automations/competitor-price-tracker/) | Marketing | Scrape competitor pricing pages, alert on changes |
| [linkedin-ai-content-poster](automations/linkedin-ai-content-poster/) | Marketing / AI | Fully autonomous LinkedIn content pipeline |
| [multi-page-web-scraper](automations/multi-page-web-scraper/) | Tech | Configurable recursive scraper with pagination support |
| [news-aggregator](automations/news-aggregator/) | Tech | Pull from NewsAPI, Mediastack, CurrentsAPI into one store |
| [facebook-ad-ai-analyser](automations/facebook-ad-ai-analyser/) | AI / Marketing | Score ad creatives against account benchmarks with Gemini |
| [b2b-lead-researcher](automations/b2b-lead-researcher/) | AI / Tech | Scrape company pages, synthesise into Airtable CRM records |
| [competitor-campaign-monitor](automations/competitor-campaign-monitor/) | Marketing / Tech | Weekly Slack digest of competitor page changes |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Basic rule: if it needs more than 15 minutes of setup to get running, it's not ready.

---

## 📄 License

MIT — use it, break it, improve it.
