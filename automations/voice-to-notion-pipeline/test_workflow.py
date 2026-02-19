"""
Tests for Voice to Notion Pipeline / workflow.py

Run:
    python -m pytest test_workflow.py -v

All external HTTP calls should be mocked — no real API credentials needed.
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch, mock_open

# ── Patch env before importing workflow so module-level config is correct ──────
os.environ.setdefault("OPENAI_API_KEY", "mock_oa_key")

import workflow  # noqa: E402


class TestVoicePipeline(unittest.TestCase):
    """Integration-level test for the router — HTTP calls mocked."""

    @patch("workflow.requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"mock_audio_data")
    @patch("os.path.exists")
    def test_pipeline_success(self, mock_exists, mock_file, mock_post):
        """Tests that a mock audio file is correctly transcribed and parsed into dict"""
        
        mock_exists.return_value = True

        # Mock requests.post to return DIFFERENT things depending on the URL
        def mock_post_dispatcher(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = lambda: None
            
            if "audio/transcriptions" in url:
                mock_resp.json.return_value = {"text": "Hey buy milk"}
            elif "chat/completions" in url:
                mock_resp.json.return_value = {
                    "choices": [{
                        "message": {
                            "content": "```json\n{\"title\": \"Buy Groceries\", \"category\": \"To-Do\", \"tags\": [\"errands\"], \"content\": \"Need to buy milk.\"}\n```"
                        }
                    }]
                }
            return mock_resp

        mock_post.side_effect = mock_post_dispatcher

        # Execute
        transcript = workflow.transcribe_audio("dummy.ogg")
        structured = workflow.process_transcript_with_llm(transcript)

        # Assertions
        self.assertEqual(transcript, "Hey buy milk")
        self.assertEqual(structured["title"], "Buy Groceries")
        self.assertEqual(structured["category"], "To-Do")
        self.assertEqual(structured["raw_transcript"], "Hey buy milk")

    def test_file_not_found(self):
        """Ensure it blows up gracefully if n8n failed to download the file"""
        # Un-mock builtins.open / os.path.exists here
        with self.assertRaises(FileNotFoundError):
            workflow.transcribe_audio("/this/file/doesnt/exist.mp3")


if __name__ == "__main__":
    unittest.main()
