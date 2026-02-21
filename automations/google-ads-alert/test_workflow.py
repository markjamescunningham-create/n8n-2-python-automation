"""
Tests for google-ads-alert/workflow.py

Run:
    python -m pytest test_workflow.py -v

All external HTTP calls are mocked — no real Google Ads or Slack credentials needed.
"""

import os
import unittest
from unittest.mock import MagicMock, patch, call

os.environ.setdefault("GOOGLE_ADS_DEVELOPER_TOKEN", "test-dev-token")
os.environ.setdefault("GOOGLE_ADS_ACCESS_TOKEN",    "test-access-token")
os.environ.setdefault("GOOGLE_ADS_CUSTOMER_ID",     "123-456-7890")
os.environ.setdefault("CPA_THRESHOLD_USD",           "50.0")
os.environ.setdefault("CPC_THRESHOLD_USD",           "5.0")
os.environ.setdefault("SLACK_BOT_TOKEN",             "xoxb-test-token")
os.environ.setdefault("SLACK_CHANNEL",               "#ads-alerts")

import workflow  # noqa: E402


# ── Fixtures ───────────────────────────────────────────────────────────────────
def make_raw_row(name="Brand keywords", cost_micros=10_000_000, clicks=500, conversions=200.0):
    return {
        "campaign": {"id": "111", "name": name, "status": "ENABLED"},
        "metrics":  {
            "costMicros":   str(cost_micros),
            "clicks":       str(clicks),
            "impressions":  "10000",
            "conversions":  str(conversions),
        },
        "segments": {"date": "2024-03-10"},
    }


MOCK_API_RESPONSE = [
    {
        "results": [
            make_raw_row("Brand keywords",      cost_micros=10_000_000, clicks=500, conversions=200),
            make_raw_row("Competitor keywords",  cost_micros=80_000_000, clicks=400, conversions=1),
            make_raw_row("Display prospecting",  cost_micros=5_000_000,  clicks=50,  conversions=0),
        ]
    }
]


class TestNormaliseRow(unittest.TestCase):

    def test_normal_campaign(self):
        raw = make_raw_row("Brand", cost_micros=10_000_000, clicks=500, conversions=200)
        result = workflow.normalise_row(raw)

        self.assertEqual(result["campaign_name"], "Brand")
        self.assertAlmostEqual(result["cost_usd"], 10.0)
        self.assertAlmostEqual(result["cpc_usd"], 0.02)      # 10 / 500
        self.assertAlmostEqual(result["cpa_usd"], 0.05)      # 10 / 200

    def test_zero_clicks_no_division_error(self):
        raw = make_raw_row("No-click campaign", clicks=0, conversions=0)
        result = workflow.normalise_row(raw)
        self.assertEqual(result["cpc_usd"], 0.0)
        self.assertEqual(result["cpa_usd"], 0.0)

    def test_zero_conversions_no_division_error(self):
        raw = make_raw_row("No-conv campaign", clicks=100, conversions=0)
        result = workflow.normalise_row(raw)
        self.assertGreater(result["cpc_usd"], 0)
        self.assertEqual(result["cpa_usd"], 0.0)

    def test_cost_micros_conversion(self):
        raw = make_raw_row(cost_micros=1_000_000, clicks=1, conversions=1)
        result = workflow.normalise_row(raw)
        self.assertAlmostEqual(result["cost_usd"], 1.0)


class TestFindOverThreshold(unittest.TestCase):

    def _make_row(self, cpc, cpa, name="test"):
        return {
            "campaign_id": "1", "campaign_name": name, "status": "ENABLED",
            "date": "2024-03-10", "impressions": 1000, "clicks": 10,
            "cost_usd": 100.0, "conversions": 2.0,
            "cpc_usd": cpc, "cpa_usd": cpa,
        }

    def test_no_flags_when_within_threshold(self):
        rows = [self._make_row(cpc=1.0, cpa=10.0)]
        flagged = workflow.find_over_threshold(rows)
        self.assertEqual(flagged, [])

    def test_flags_high_cpa(self):
        rows = [self._make_row(cpc=1.0, cpa=200.0, name="Expensive")]
        flagged = workflow.find_over_threshold(rows)
        self.assertEqual(len(flagged), 1)
        self.assertIn("CPA", flagged[0]["alert_reasons"][0])

    def test_flags_high_cpc(self):
        rows = [self._make_row(cpc=99.0, cpa=10.0, name="Expensive CPC")]
        flagged = workflow.find_over_threshold(rows)
        self.assertEqual(len(flagged), 1)
        self.assertIn("CPC", flagged[0]["alert_reasons"][0])

    def test_flags_both_cpa_and_cpc(self):
        rows = [self._make_row(cpc=99.0, cpa=200.0, name="Both")]
        flagged = workflow.find_over_threshold(rows)
        self.assertEqual(len(flagged[0]["alert_reasons"]), 2)

    def test_only_flags_breaching_campaigns(self):
        rows = [
            self._make_row(cpc=1.0,  cpa=5.0,   name="OK"),
            self._make_row(cpc=99.0, cpa=200.0,  name="Bad"),
        ]
        flagged = workflow.find_over_threshold(rows)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["campaign_name"], "Bad")


class TestFetchCampaignPerformance(unittest.TestCase):

    def test_missing_credentials_skip(self):
        orig_token = workflow.GOOGLE_ADS_ACCESS_TOKEN
        workflow.GOOGLE_ADS_ACCESS_TOKEN = ""
        result = workflow.fetch_campaign_performance("2024-03-10")
        workflow.GOOGLE_ADS_ACCESS_TOKEN = orig_token
        self.assertEqual(result, [])

    def test_missing_customer_id_skip(self):
        orig = workflow.GOOGLE_ADS_CUSTOMER_ID
        workflow.GOOGLE_ADS_CUSTOMER_ID = ""
        result = workflow.fetch_campaign_performance("2024-03-10")
        workflow.GOOGLE_ADS_CUSTOMER_ID = orig
        self.assertEqual(result, [])

    @patch("workflow.requests.post")
    def test_returns_results(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: MOCK_API_RESPONSE,
            raise_for_status=lambda: None,
        )
        rows = workflow.fetch_campaign_performance("2024-03-10")
        self.assertEqual(len(rows), 3)


class TestSendSlackAlert(unittest.TestCase):

    @patch("workflow.requests.post")
    def test_no_call_when_empty(self, mock_post):
        workflow.send_slack_alert([])
        mock_post.assert_not_called()

    @patch("workflow.requests.post")
    def test_alert_posted_when_flagged(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"ok": True},
            raise_for_status=lambda: None,
        )
        row = {
            "campaign_id": "1", "campaign_name": "Bad campaign",
            "date": "2024-03-10", "cpa_usd": 200.0, "cpc_usd": 99.0,
            "alert_reasons": ["CPA $200.00 > $50.00"],
            "cost_usd": 200.0, "clicks": 2, "conversions": 1.0,
        }
        workflow.send_slack_alert([row])
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("Bad campaign", kwargs["json"]["text"])

    def test_skip_when_no_token(self):
        orig = workflow.SLACK_BOT_TOKEN
        workflow.SLACK_BOT_TOKEN = ""
        # Should not raise
        row = {
            "campaign_name": "test", "date": "2024-03-10",
            "alert_reasons": ["CPA $200.00 > $50.00"],
        }
        workflow.send_slack_alert([row])
        workflow.SLACK_BOT_TOKEN = orig


class TestMain(unittest.TestCase):

    @patch("workflow.requests.post")
    def test_main_no_flags(self, mock_post):
        """When all campaigns are within thresholds, no Slack message is sent."""
        safe_raw_response = [{
            "results": [make_raw_row("Brand", cost_micros=100_000, clicks=50, conversions=10)]
        }]
        mock_post.return_value = MagicMock(
            json=lambda: safe_raw_response,
            raise_for_status=lambda: None,
        )
        result = workflow.main()
        self.assertEqual(result["flagged"], [])
        # Only the Google Ads POST should be called, not Slack
        self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
