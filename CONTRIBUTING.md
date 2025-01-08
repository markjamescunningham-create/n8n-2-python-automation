# Contributing

Thanks for wanting to add an automation — contributions are welcome from everyone.

---

## Adding an Automation

### 1. Copy the template

```bash
cp -r templates/automation-template automations/your-automation-name
```

Use **lowercase-with-hyphens** for the folder name (e.g. `slack-to-notion`, `openai-lead-enrichment`).

### 2. Fill in the required files

| File | Required | Notes |
|------|----------|-------|
| `README.md` | ✅ | Describe what it does, inputs, outputs, and setup steps |
| `workflow.json` | ✅ | n8n workflow export. Export via n8n → ⋯ → Download |
| `workflow.py` | ✅ | Python script that replicates the same logic |
| `.env.example` | ✅ if using secrets | List every env var the script needs (no real values) |
| `requirements.txt` | If needed | Python dependencies |
| `assets/` | Optional | Screenshots, diagrams |

### 3. Checklist before submitting a PR

- [ ] Folder name follows the `lowercase-with-hyphens` convention
- [ ] `README.md` explains the use case clearly, including any required credentials
- [ ] `workflow.json` is a valid n8n export (not a blank file)
- [ ] `workflow.py` runs with `python workflow.py` after installing dependencies
- [ ] `.env.example` is included if the script uses any API keys or secrets (no real values)
- [ ] No hardcoded credentials anywhere in the code
- [ ] The automation is listed in the root `README.md` table

### 4. Open a Pull Request

Title format: `[Category] Short description` — e.g. `[AI] Summarise URL with OpenAI`

---

## Categories

Use one of these in your PR title and README:

- `AI` — LLM, embeddings, agents, vector search
- `Marketing` — Email, social, CRM, analytics
- `Tech` — DevOps, APIs, databases, GitHub, Notion
- `General` — Utilities that don't fit neatly elsewhere

---

## Code Style (Python)

- Python 3.10+
- Use `python-dotenv` for environment variables
- Keep scripts self-contained — avoid deeply nested project structures
- Add a `if __name__ == "__main__":` block
- Include a short docstring at the top of the file explaining what the script does
