from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from meeting_summary.models import TranscriptionResult
from meeting_summary.ollama_client import OllamaClient, OllamaError


def make_response(status_code: int, payload: dict[str, object], text: str = "") -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = text or str(payload)
    response.raise_for_status.side_effect = None if status_code < 400 else Exception(text)
    return response


class OllamaClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transcription = TranscriptionResult(
            source_path=Path("calls/demo.m4a"),
            transcript="Тестовая расшифровка",
            language="ru",
            duration_seconds=10.0,
        )

    @patch("meeting_summary.ollama_client.requests.get")
    @patch("meeting_summary.ollama_client.requests.post")
    def test_auto_model_uses_first_installed_model(self, post_mock: Mock, get_mock: Mock) -> None:
        get_mock.return_value = make_response(
            200,
            {"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.1:8b"}]},
        )
        post_mock.return_value = make_response(200, {"response": "Готовое summary"})

        client = OllamaClient(base_url="http://localhost:11434", model="auto")
        result = client.summarize(self.transcription)

        self.assertEqual(result.content, "Готовое summary")
        self.assertEqual(client.model, "qwen2.5:7b")
        self.assertEqual(post_mock.call_args.kwargs["json"]["model"], "qwen2.5:7b")

    @patch("meeting_summary.ollama_client.requests.get")
    @patch("meeting_summary.ollama_client.requests.post")
    def test_missing_configured_model_falls_back_to_installed_model(
        self,
        post_mock: Mock,
        get_mock: Mock,
    ) -> None:
        post_mock.side_effect = [
            make_response(404, {"error": "model 'gemma3:4b' not found"}),
            make_response(200, {"response": "Summary via fallback"}),
        ]
        get_mock.return_value = make_response(
            200,
            {"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:7b"}]},
        )

        client = OllamaClient(base_url="http://localhost:11434", model="gemma3:4b")
        result = client.summarize(self.transcription)

        self.assertEqual(result.content, "Summary via fallback")
        self.assertEqual(client.model, "llama3.1:8b")
        self.assertEqual(post_mock.call_count, 2)

    @patch("meeting_summary.ollama_client.requests.get")
    @patch("meeting_summary.ollama_client.requests.post")
    def test_missing_configured_model_without_local_models_raises_clear_error(
        self,
        post_mock: Mock,
        get_mock: Mock,
    ) -> None:
        post_mock.return_value = make_response(404, {"error": "model 'gemma3:4b' not found"})
        get_mock.return_value = make_response(200, {"models": []})

        client = OllamaClient(base_url="http://localhost:11434", model="gemma3:4b")

        with self.assertRaises(OllamaError) as error:
            client.summarize(self.transcription)

        self.assertIn("gemma3:4b", str(error.exception))
        self.assertIn("Available local models: none", str(error.exception))


if __name__ == "__main__":
    unittest.main()
