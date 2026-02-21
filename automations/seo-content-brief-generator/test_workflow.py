"""
Tests for seo-content-brief-generator/workflow.py

Run:
    python -m pytest test_workflow.py -v

All external calls (SerpAPI, OpenAI) are mocked — no real API keys needed.
"""

import json
import os
import shutil
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("SERPAPI_KEY",    "test-serp-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("OPENAI_MODEL",   "gpt-4o-mini")
os.environ.setdefault("SERP_RESULTS",   "5")
os.environ.setdefault("KEYWORD",        "best project management software")
os.environ.setdefault("OUTPUT_DIR",     "/tmp/test_briefs")

import workflow  # noqa: E402


# ── Fixture data ───────────────────────────────────────────────────────────────
MOCK_SERP_RESPONSE = {
    "organic_results": [
        {"position": 1, "title": "Top 10 PM Tools 2024", "link": "https://example.com/1", "snippet": "Great tools..."},
        {"position": 2, "title": "Best PM Software Reviewed", "link": "https://example.com/2", "snippet": "Reviewed by experts..."},
        {"position": 3, "title": "Project Management Guide", "link": "https://example.com/3", "snippet": "A complete guide..."},
    ]
}

MOCK_BRIEF = {
    "recommended_title": "The 15 Best Project Management Software Tools for 2024",
    "meta_description": "Compare the best project management tools. Expert reviews, pricing, and feature breakdowns to help you choose.",
    "target_word_count": 3500,
    "primary_keyword": "best project management software",
    "secondary_keywords": ["project management tools", "PM software comparison", "team collaboration tools"],
    "content_angle": "A feature-comparison guide emphasising ROI and team adoption rather than just listing features.",
    "outline": [
        {"heading": "What to Look for in PM Software", "subheadings": ["Must-have features", "Nice-to-haves"]},
        {"heading": "Top 15 Tools Compared", "subheadings": ["Asana", "Monday.com", "Notion"]},
        {"heading": "How to Choose the Right Tool", "subheadings": ["Team size", "Budget"]},
    ],
    "key_topics_to_cover": ["Pricing tiers", "Integration options", "Free trial availability"],
    "things_to_avoid": ["Overly technical jargon", "Promoting a single tool without comparison"],
}


class TestSlug(unittest.TestCase):

    def test_basic_keyword(self):
        self.assertEqual(workflow.slug("best CRM for startups"), "best-crm-for-startups")

    def test_special_chars(self):
        self.assertEqual(workflow.slug("AI & ML tools 2024!"), "ai-ml-tools-2024")

    def test_already_slugged(self):
        self.assertEqual(workflow.slug("keyword-here"), "keyword-here")


class TestFetchSerpResults(unittest.TestCase):

    @patch("workflow.requests.get")
    def test_returns_normalised_results(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: MOCK_SERP_RESPONSE,
            raise_for_status=lambda: None,
        )
        results = workflow.fetch_serp_results("best project management software")

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["position"], 1)
        self.assertEqual(results[0]["title"], "Top 10 PM Tools 2024")
        self.assertIn("link", results[0])
        self.assertIn("snippet", results[0])

    @patch("workflow.requests.get")
    def test_respects_serp_results_limit(self, mock_get):
        # Return 3 results but SERP_RESULTS is 5 — should return all 3
        mock_get.return_value = MagicMock(
            json=lambda: MOCK_SERP_RESPONSE,
            raise_for_status=lambda: None,
        )
        results = workflow.fetch_serp_results("test keyword")
        self.assertLessEqual(len(results), workflow.SERP_RESULTS)

    def test_missing_key_returns_empty(self):
        orig = workflow.SERPAPI_KEY
        workflow.SERPAPI_KEY = ""
        results = workflow.fetch_serp_results("anything")
        workflow.SERPAPI_KEY = orig
        self.assertEqual(results, [])


class TestBuildPrompts(unittest.TestCase):

    def test_system_prompt_contains_schema(self):
        prompt = workflow.build_system_prompt()
        self.assertIn("recommended_title", prompt)
        self.assertIn("outline", prompt)
        self.assertIn("meta_description", prompt)

    def test_user_prompt_contains_keyword(self):
        keyword = "content marketing tools"
        results = [{"position": 1, "title": "Test", "snippet": "Test snippet"}]
        prompt = workflow.build_user_prompt(keyword, results)
        self.assertIn(keyword, prompt)
        self.assertIn("Test", prompt)


class TestGenerateBrief(unittest.TestCase):

    @patch("workflow.OpenAI")
    def test_returns_parsed_json(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(MOCK_BRIEF)))]
        )
        MockOpenAI.return_value = mock_client

        serp_results = [{"position": 1, "title": "Test", "snippet": "Test"}]
        result = workflow.generate_brief("best PM software", serp_results)

        self.assertEqual(result["recommended_title"], MOCK_BRIEF["recommended_title"])
        self.assertEqual(result["target_word_count"], 3500)
        self.assertIsInstance(result["outline"], list)

    def test_missing_openai_key_raises(self):
        orig = workflow.OPENAI_API_KEY
        workflow.OPENAI_API_KEY = ""
        with self.assertRaises(ValueError):
            workflow.generate_brief("keyword", [])
        workflow.OPENAI_API_KEY = orig


class TestSaveBrief(unittest.TestCase):

    def setUp(self):
        workflow.OUTPUT_DIR = "/tmp/test_briefs_save"

    def tearDown(self):
        shutil.rmtree("/tmp/test_briefs_save", ignore_errors=True)

    def test_creates_markdown_file(self):
        filepath = workflow.save_brief("best PM software", MOCK_BRIEF, [])
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.endswith(".md"))

    def test_file_contains_title(self):
        filepath = workflow.save_brief("best PM software", MOCK_BRIEF, [])
        with open(filepath) as f:
            content = f.read()
        self.assertIn(MOCK_BRIEF["recommended_title"], content)

    def test_file_contains_outline_headings(self):
        filepath = workflow.save_brief("best PM software", MOCK_BRIEF, [])
        with open(filepath) as f:
            content = f.read()
        self.assertIn("What to Look for in PM Software", content)


class TestMain(unittest.TestCase):

    def setUp(self):
        workflow.OUTPUT_DIR = "/tmp/test_briefs_main"

    def tearDown(self):
        shutil.rmtree("/tmp/test_briefs_main", ignore_errors=True)

    @patch("workflow.OpenAI")
    @patch("workflow.requests.get")
    def test_main_returns_result(self, mock_get, MockOpenAI):
        mock_get.return_value = MagicMock(
            json=lambda: MOCK_SERP_RESPONSE,
            raise_for_status=lambda: None,
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(MOCK_BRIEF)))]
        )
        MockOpenAI.return_value = mock_client

        result = workflow.main("best project management software")

        self.assertEqual(result["keyword"], "best project management software")
        self.assertIn("brief", result)
        self.assertIn("output_file", result)
        self.assertTrue(os.path.exists(result["output_file"]))

    def test_main_no_keyword_raises(self):
        orig = workflow.KEYWORD
        workflow.KEYWORD = ""
        with self.assertRaises(ValueError):
            workflow.main(keyword=None)
        workflow.KEYWORD = orig


if __name__ == "__main__":
    unittest.main()
