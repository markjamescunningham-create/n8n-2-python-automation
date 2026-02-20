"""
Tests for Invoice Vision Processor / workflow.py

Run:
    python -m pytest test_workflow.py -v

All external HTTP calls should be mocked — no real API credentials needed.
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch

# ── Patch env before importing workflow so module-level config is correct ──────
os.environ.setdefault("OPENAI_API_KEY", "mock_oa_key")

import workflow  # noqa: E402


class TestInvoiceProcessor(unittest.TestCase):
    """Integration-level test — HTTP calls mocked."""

    @patch("workflow.requests.post")
    @patch("workflow.extract_text_from_pdf")
    def test_pipeline_success(self, mock_pdf, mock_post):
        """Tests that raw pdf text is transformed successfully into a typed dict"""
        
        mock_pdf.return_value = "INVOICE #1023\nStripe, Inc.\nDate: 2026/05/14\nPayment processor fees\nTotal: $3,450.50"

        mock_post.return_value = MagicMock(
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": "```json\n{\"vendor\": \"Stripe, Inc.\", \"amount\": 3450.50, \"date\": \"2026-05-14\", \"description\": \"Payment processor fees\", \"confidence\": \"high\"}\n```"
                    }
                }]
            },
            raise_for_status=lambda: None
        )

        # Execute
        raw_text = workflow.extract_text_from_pdf("dummy.pdf")
        structured = workflow.parse_invoice_with_llm(raw_text)

        # Assertions
        self.assertEqual(structured["vendor"], "Stripe, Inc.")
        
        # Testing float casting
        self.assertIsInstance(structured["amount"], float)
        self.assertEqual(structured["amount"], 3450.50)
        
        self.assertEqual(structured["date"], "2026-05-14")
        self.assertEqual(structured["confidence"], "high")

    @patch("workflow.requests.post")
    @patch("workflow.extract_text_from_pdf")
    def test_pipeline_json_error(self, mock_pdf, mock_post):
        """Tests failing gracefully when the LLM hallucinates non-JSON"""
        
        mock_pdf.return_value = "Some text"

        mock_post.return_value = MagicMock(
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": "Sorry, I can't do that. Here's what I found: Vendor was Acme."
                    }
                }]
            },
            raise_for_status=lambda: None
        )

        with self.assertRaises(ValueError) as context:
            workflow.parse_invoice_with_llm("test")

        self.assertIn("Failed to parse LLM JSON", str(context.exception))


if __name__ == "__main__":
    unittest.main()
