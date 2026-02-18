"""
Tests for Lead Enrichment Router / workflow.py

Run:
    python -m pytest test_workflow.py -v

All external HTTP calls should be mocked — no real API credentials needed.
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch

# ── Patch env before importing workflow so module-level config is correct ──────
os.environ.setdefault("CLEARBIT_API_KEY", "mock_cb_key")
os.environ.setdefault("OPENAI_API_KEY", "mock_oa_key")

import workflow  # noqa: E402


class TestLeadEnrichment(unittest.TestCase):
    """Integration-level test for the router — HTTP calls mocked."""

    @patch("workflow.requests.post")
    @patch("workflow.requests.get")
    def test_hot_lead_flow(self, mock_get, mock_post):
        """Tests that an executive at a software company gets a high score and routes to 'sales'"""
        
        # 1. Mock the Clearbit GET response
        mock_get.return_value = MagicMock(
            json=lambda: {
                "person": {"employment": {"role": "CEO"}},
                "company": {"name": "Acme Software", "category": {"sector": "Technology"}, "metrics": {"employees": "1k-5k"}}
            },
            raise_for_status=lambda: None,
        )
        
        # 2. Mock the OpenAI POST response
        mock_post.return_value = MagicMock(
            json=lambda: {
                "choices": [{
                    "message": {
                        # Note: formatting purposefully includes some backticks to test our regex cleanup
                        "content": "```json\n{\"score\": 95, \"reason\": \"CEO at large tech corp.\"}\n```"
                    }
                }]
            },
            raise_for_status=lambda: None
        )

        # Execute
        email = "test@acmesoftware.com"
        enriched = workflow.fetch_clearbit_data(email)
        scored = workflow.score_lead_with_ai(email, enriched)
        
        final_result = {"email": email, **enriched, **scored}

        # Assert Clearbit parsing
        self.assertEqual(final_result["industry"], "Technology")
        self.assertEqual(final_result["seniority"], "CEO")
        self.assertEqual(final_result["company_name"], "Acme Software")
        
        # Assert AI scoring & Routing
        self.assertEqual(final_result["score"], 95)
        self.assertEqual(final_result["routing_dest"], "sales")


    @patch("workflow.requests.get")
    def test_clearbit_404_handling(self, mock_get):
        """Tests that returning a 404 from Clearbit (person not found) doesn't crash the script"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        
        import requests
        err = requests.exceptions.HTTPError()
        err.response = mock_resp
        
        mock_get.side_effect = err
        
        res = workflow.fetch_clearbit_data("ghost@nobody.com")
        self.assertEqual(res["company_name"], "Unknown")
        self.assertEqual(res["mocked"], False)


if __name__ == "__main__":
    unittest.main()
