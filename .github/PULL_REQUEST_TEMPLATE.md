## Description

Please include a summary of the new automation or bug fix. 

Fixes # (issue)

## Checklist before requesting a review

- [ ] Folder name follows the `lowercase-with-hyphens` convention (e.g. `slack-to-notion`).
- [ ] `README.md` explains the use case clearly, including any required credentials.
- [ ] `workflow.json` is included and is a valid n8n export.
- [ ] `workflow.py` replicates the exact same logic.
- [ ] `test_workflow.py` is included (using `unittest` or `pytest`) and mocks all external API calls.
- [ ] `.env.example` is included (no real keys!).
- [ ] No hardcoded credentials anywhere in the code.
- [ ] I've added my automation to the table in the root `README.md`.
