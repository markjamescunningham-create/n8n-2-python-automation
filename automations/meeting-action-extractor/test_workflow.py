"""
Tests for meeting-action-extractor/workflow.py

Run:
    python -m pytest test_workflow.py -v

All external calls (OpenAI, Notion) are mocked — no real API keys needed.
"""

import csv
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY",  "test-openai-key")
os.environ.setdefault("OPENAI_MODEL",    "gpt-4o-mini")
os.environ.setdefault("NOTION_API_KEY",  "secret_test")
os.environ.setdefault("NOTION_DB_ID",    "db-abc-123")

import workflow  # noqa: E402


# ── Test transcript ────────────────────────────────────────────────────────────
SAMPLE_TRANSCRIPT = """
Alice: Great meeting everyone. Mark, can you send the Q1 report to the board by Friday?
Mark: Sure, I'll get that done by March 15th.
Alice: And Sarah, can you set up the demo environment for the client call next Tuesday?
Sarah: Yes, I'll have it ready. Low priority for now since the call is far out.
Bob: I'll follow up with the vendor about the contract. No deadline yet.
"""

MOCK_ITEMS = [
    {
        "owner":    "Mark",
        "task":     "Send the Q1 report to the board",
        "due_date": "2024-03-15",
        "priority": "High",
        "context":  "Alice asked Mark to send the Q1 report to the board by Friday.",
    },
    {
        "owner":    "Sarah",
        "task":     "Set up the demo environment for the client call",
        "due_date": "2024-03-19",
        "priority": "Low",
        "context":  "Sarah needs to set up the demo environment before next Tuesday.",
    },
    {
        "owner":    "Bob",
        "task":     "Follow up with vendor about the contract",
        "due_date": None,
        "priority": "Medium",
        "context":  "Bob to follow up with the vendor; no deadline set.",
    },
]


class TestLoadTranscript(unittest.TestCase):

    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(SAMPLE_TRANSCRIPT)
            name = f.name
        try:
            text = workflow.load_transcript(name)
            self.assertIn("Alice", text)
            self.assertIn("Mark", text)
        finally:
            os.unlink(name)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            workflow.load_transcript("/tmp/this_file_does_not_exist_abc.txt")

    @patch("workflow.sys.stdin")
    def test_no_source_raises(self, mock_stdin):
        # Simulate a tty (no piped input) so load_transcript raises ValueError
        mock_stdin.isatty.return_value = True
        orig = workflow.TRANSCRIPT_FILE
        workflow.TRANSCRIPT_FILE = ""
        with self.assertRaises(ValueError):
            workflow.load_transcript(None)
        workflow.TRANSCRIPT_FILE = orig


class TestExtractActionItems(unittest.TestCase):

    @patch("workflow.OpenAI")
    def test_returns_list_of_items(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(MOCK_ITEMS)))]
        )
        MockOpenAI.return_value = mock_client

        items = workflow.extract_action_items(SAMPLE_TRANSCRIPT)

        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["owner"], "Mark")
        self.assertEqual(items[0]["due_date"], "2024-03-15")
        self.assertEqual(items[0]["priority"], "High")

    @patch("workflow.OpenAI")
    def test_handles_wrapped_response(self, MockOpenAI):
        """GPT sometimes wraps the list in {"action_items": [...]}."""
        wrapped = {"action_items": MOCK_ITEMS}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(wrapped)))]
        )
        MockOpenAI.return_value = mock_client

        items = workflow.extract_action_items(SAMPLE_TRANSCRIPT)
        self.assertEqual(len(items), 3)

    @patch("workflow.OpenAI")
    def test_empty_transcript_returns_empty(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="[]"))]
        )
        MockOpenAI.return_value = mock_client

        items = workflow.extract_action_items("")
        self.assertEqual(items, [])

    def test_missing_api_key_raises(self):
        orig = workflow.OPENAI_API_KEY
        workflow.OPENAI_API_KEY = ""
        with self.assertRaises(ValueError):
            workflow.extract_action_items(SAMPLE_TRANSCRIPT)
        workflow.OPENAI_API_KEY = orig


class TestSaveToCSV(unittest.TestCase):

    def test_creates_csv_with_correct_headers(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            name = f.name
        os.unlink(name)  # Remove so save_to_csv creates fresh
        try:
            workflow.save_to_csv(MOCK_ITEMS, filepath=name)
            with open(name) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 3)
            self.assertIn("owner", rows[0])
            self.assertIn("task", rows[0])
            self.assertEqual(rows[0]["owner"], "Mark")
        finally:
            os.unlink(name)

    def test_appends_on_second_run(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            name = f.name
        os.unlink(name)
        try:
            workflow.save_to_csv(MOCK_ITEMS[:1], filepath=name)
            workflow.save_to_csv(MOCK_ITEMS[1:], filepath=name)
            with open(name) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 3)
        finally:
            os.unlink(name)

    def test_null_due_date_written_as_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            name = f.name
        os.unlink(name)
        try:
            workflow.save_to_csv([MOCK_ITEMS[2]], filepath=name)  # Bob — no due date
            with open(name) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(rows[0]["due_date"], "")
        finally:
            os.unlink(name)


class TestPushToNotion(unittest.TestCase):

    @patch("workflow.requests.post")
    def test_creates_page_per_item(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        workflow.push_to_notion(MOCK_ITEMS)
        self.assertEqual(mock_post.call_count, 3)

    @patch("workflow.requests.post")
    def test_no_push_when_missing_credentials(self, mock_post):
        orig_key = workflow.NOTION_API_KEY
        orig_db  = workflow.NOTION_DB_ID
        workflow.NOTION_API_KEY = ""
        workflow.NOTION_DB_ID   = ""
        workflow.push_to_notion(MOCK_ITEMS)
        mock_post.assert_not_called()
        workflow.NOTION_API_KEY = orig_key
        workflow.NOTION_DB_ID   = orig_db

    @patch("workflow.requests.post")
    def test_null_due_date_excluded_from_payload(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        # Bob has no due_date
        workflow.push_to_notion([MOCK_ITEMS[2]])
        _, kwargs = mock_post.call_args
        props = kwargs["json"]["properties"]
        self.assertNotIn("Due Date", props)


class TestMain(unittest.TestCase):

    @patch("workflow.requests.post")
    @patch("workflow.OpenAI")
    def test_main_end_to_end(self, MockOpenAI, mock_post):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(MOCK_ITEMS)))]
        )
        MockOpenAI.return_value = mock_client
        mock_post.return_value  = MagicMock(status_code=200)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(SAMPLE_TRANSCRIPT)
            transcript_path = f.name

        orig_csv = workflow.OUTPUT_CSV
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            workflow.OUTPUT_CSV = f.name
        try:
            items = workflow.main(transcript_path=transcript_path)
            self.assertEqual(len(items), 3)
            # Notion POST should have been called 3 times
            self.assertEqual(mock_post.call_count, 3)
        finally:
            os.unlink(transcript_path)
            os.unlink(workflow.OUTPUT_CSV)
            workflow.OUTPUT_CSV = orig_csv

    @patch("workflow.OpenAI")
    def test_main_no_items(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="[]"))]
        )
        MockOpenAI.return_value = mock_client

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Just a casual chat with no tasks mentioned.")
            path = f.name
        try:
            items = workflow.main(transcript_path=path)
            self.assertEqual(items, [])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
