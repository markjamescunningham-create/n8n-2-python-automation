"""
Tests for email-performance-reporter/workflow.py

Run:
    python -m pytest test_workflow.py -v
    # or: python -m unittest test_workflow -v

All external HTTP calls are mocked — no real Mailchimp or Sheets credentials needed.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

# ── Patch env before importing workflow so module-level config is correct ──────
os.environ.setdefault("MAILCHIMP_API_KEY", "test-key")
os.environ.setdefault("MAILCHIMP_SERVER", "us1")
os.environ.setdefault("MAILCHIMP_LIST_ID", "abc123")
os.environ.setdefault("CAMPAIGN_LIMIT", "5")
os.environ.setdefault("SHEETS_WEBHOOK_URL", "https://example.com/webhook")

import workflow  # noqa: E402  (import after env patch)


# ── Fixtures ───────────────────────────────────────────────────────────────────
MOCK_CAMPAIGN = {
    "id": "camp_001",
    "send_time": "2024-03-11T08:00:00+00:00",
    "settings": {"subject_line": "March newsletter 🎉"},
    "report_summary": {
        "subscriber_count": 1000,
        "unique_opens":     450,
        "unique_clicks":    80,
        "unsubscribed":     5,
    },
}

MOCK_EMPTY_CAMPAIGN = {
    "id": "camp_002",
    "send_time": "2024-03-04T08:00:00+00:00",
    "settings": {"subject_line": "Empty report campaign"},
    "report_summary": {},
}


class TestExtractMetrics(unittest.TestCase):
    """Unit tests for the metrics extraction logic — no HTTP calls."""

    def test_happy_path(self):
        result = workflow.extract_metrics(MOCK_CAMPAIGN)

        self.assertEqual(result["campaign_id"], "camp_001")
        self.assertEqual(result["subject_line"], "March newsletter 🎉")
        self.assertEqual(result["recipients"], 1000)
        self.assertEqual(result["opens"], 450)
        self.assertEqual(result["click_rate_pct"], 8.0)
        self.assertEqual(result["open_rate_pct"], 45.0)
        self.assertEqual(result["unsubscribe_rate_pct"], 0.5)
        self.assertIn("retrieved_at", result)

    def test_zero_recipients_no_division_error(self):
        zero_campaign = {
            "id": "camp_zero",
            "send_time": "2024-01-01T00:00:00+00:00",
            "settings": {"subject_line": "Zero send"},
            "report_summary": {
                "subscriber_count": 0,
                "unique_opens":     0,
                "unique_clicks":    0,
                "unsubscribed":     0,
            },
        }
        result = workflow.extract_metrics(zero_campaign)
        self.assertEqual(result["open_rate_pct"], 0.0)
        self.assertEqual(result["click_rate_pct"], 0.0)
        self.assertEqual(result["unsubscribe_rate_pct"], 0.0)

    def test_missing_report_summary_fields(self):
        result = workflow.extract_metrics(MOCK_EMPTY_CAMPAIGN)
        self.assertEqual(result["recipients"], 0)
        self.assertEqual(result["open_rate_pct"], 0.0)


class TestFetchCampaigns(unittest.TestCase):
    """Tests for the Mailchimp fetch — HTTP call mocked."""

    @patch("workflow.requests.get")
    def test_fetch_returns_campaigns(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"campaigns": [MOCK_CAMPAIGN]}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = workflow.fetch_campaigns()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "camp_001")

    @patch("workflow.requests.get")
    def test_fetch_empty_list(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"campaigns": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = workflow.fetch_campaigns()
        self.assertEqual(result, [])

    def test_missing_api_key_skips(self):
        original = workflow.MAILCHIMP_API_KEY
        workflow.MAILCHIMP_API_KEY = ""
        result = workflow.fetch_campaigns()
        workflow.MAILCHIMP_API_KEY = original
        self.assertEqual(result, [])


class TestSendToSheets(unittest.TestCase):
    """Tests for the Sheets push — HTTP call mocked."""

    @patch("workflow.requests.post")
    def test_post_called_with_correct_payload(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        rows = [workflow.extract_metrics(MOCK_CAMPAIGN)]

        workflow.send_to_sheets(rows)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["rows"], rows)

    def test_missing_webhook_url_skips(self):
        original = workflow.SHEETS_WEBHOOK_URL
        workflow.SHEETS_WEBHOOK_URL = ""
        # Should not raise
        workflow.send_to_sheets([])
        workflow.SHEETS_WEBHOOK_URL = original


class TestMain(unittest.TestCase):
    """Integration-level test — both HTTP calls mocked."""

    @patch("workflow.requests.post")
    @patch("workflow.requests.get")
    def test_main_returns_rows(self, mock_get, mock_post):
        mock_get.return_value = MagicMock(
            json=lambda: {"campaigns": [MOCK_CAMPAIGN, MOCK_EMPTY_CAMPAIGN]},
            raise_for_status=lambda: None,
        )
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)

        rows = workflow.main()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["campaign_id"], "camp_001")

    @patch("workflow.requests.get")
    def test_main_no_campaigns_returns_empty(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"campaigns": []},
            raise_for_status=lambda: None,
        )
        rows = workflow.main()
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
