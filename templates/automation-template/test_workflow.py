"""
Tests for [Automation Name]/workflow.py

Run:
    python -m pytest test_workflow.py -v

All external HTTP calls should be mocked — no real API credentials needed.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

# ── Patch env before importing workflow so module-level config is correct ──────
os.environ.setdefault("EXAMPLE_API_KEY", "test-key")

import workflow  # noqa: E402


class TestExampleExtraction(unittest.TestCase):
    """Unit tests for the data parsing logic — no HTTP calls."""

    def test_happy_path(self):
        # ... write tests here ...
        pass


class TestMain(unittest.TestCase):
    """Integration-level test — HTTP calls mocked."""

    @patch("workflow.requests.get")
    def test_main_success(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"data": "test"},
            raise_for_status=lambda: None,
        )

        # result = workflow.main()
        # self.assertEqual(result, expected)
        pass


if __name__ == "__main__":
    unittest.main()
