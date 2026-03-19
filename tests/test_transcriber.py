from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from meeting_summary.transcriber import Transcriber


class _FakeModel:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[tuple[str, bool]] = []

    def transcribe(self, audio_path: str, fp16: bool = False) -> dict[str, object]:
        self.calls.append((audio_path, fp16))
        return self.result


class TranscriberTests(unittest.TestCase):
    def test_transcribe_maps_whisper_segments_to_result(self) -> None:
        fake_model = _FakeModel(
            {
                "language": "ru",
                "segments": [
                    {"text": " Привет ", "start": 0.0, "end": 1.25},
                    {"text": " ", "start": 1.25, "end": 1.5},
                    {"text": "мир", "start": 1.5, "end": 2.75},
                ],
            }
        )
        fake_whisper = SimpleNamespace(
            load_model=lambda name, device=None: self.assertEqual(
                (name, device), ("medium", "cpu")
            )
            or fake_model
        )
        fake_torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: False),
        )

        with patch.dict("sys.modules", {"whisper": fake_whisper, "torch": fake_torch}):
            transcriber = Transcriber(model_name="medium", device="auto")
            result = transcriber.transcribe(Path("demo.m4a"))

        self.assertEqual(result.transcript, "Привет мир")
        self.assertEqual(result.language, "ru")
        self.assertEqual(result.duration_seconds, 2.75)
        self.assertEqual(fake_model.calls, [("demo.m4a", False)])
        self.assertEqual(len(result.utterances), 2)
        self.assertEqual(result.utterances[0].text, "Привет")
        self.assertEqual(result.utterances[1].text, "мир")

    def test_transcribe_uses_fp16_on_cuda(self) -> None:
        fake_model = _FakeModel(
            {
                "language": "ru",
                "segments": [{"text": "тест", "start": 0.0, "end": 1.0}],
            }
        )
        fake_whisper = SimpleNamespace(
            load_model=lambda name, device=None: self.assertEqual(
                (name, device), ("small", "cuda")
            )
            or fake_model
        )

        with patch.dict("sys.modules", {"whisper": fake_whisper}):
            transcriber = Transcriber(model_name="small", device="cuda")
            transcriber.transcribe(Path("gpu-demo.m4a"))

        self.assertEqual(fake_model.calls, [("gpu-demo.m4a", True)])

    def test_transcribe_raises_on_empty_transcript(self) -> None:
        fake_model = _FakeModel({"language": "ru", "segments": [{"text": "   "}]})
        fake_whisper = SimpleNamespace(load_model=lambda *args, **kwargs: fake_model)

        with patch.dict("sys.modules", {"whisper": fake_whisper}):
            transcriber = Transcriber(model_name="small", device="cpu")

        with self.assertRaisesRegex(RuntimeError, "empty"):
            transcriber.transcribe(Path("empty.m4a"))


if __name__ == "__main__":
    unittest.main()
