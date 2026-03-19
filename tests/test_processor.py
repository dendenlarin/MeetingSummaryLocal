from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from meeting_summary.models import CallSummary, TranscriptionResult
from meeting_summary.processor import CallProcessor


class _FakeTranscriber:
    def __init__(self) -> None:
        self.progress_callback = None

    def transcribe(self, audio_path: Path, progress_callback=None) -> TranscriptionResult:  # noqa: ANN001
        self.progress_callback = progress_callback
        if progress_callback is not None:
            progress_callback("transcribing", 20, "Transcribing audio with faster-whisper.")
            progress_callback("transcription_complete", 55, "Collected 1 transcript segments.")
            progress_callback("diarization_skipped", 75, "Diarization disabled.")

        return TranscriptionResult(
            source_path=audio_path,
            transcript="Тест",
            language="ru",
            duration_seconds=1.0,
        )


class ProcessorTests(unittest.TestCase):
    def test_process_logs_stage_progress_in_order(self) -> None:
        transcriber = _FakeTranscriber()
        ollama_client = Mock()
        ollama_client.summarize.return_value = CallSummary(content="Summary")
        processor = CallProcessor(transcriber=transcriber, ollama_client=ollama_client)
        processor._write_markdown = Mock()

        with patch("meeting_summary.processor.LOGGER") as logger_mock:
            result = processor.process(Path("calls/demo.m4a"))

        self.assertEqual(result, Path("calls/demo.md"))
        self.assertIsNotNone(transcriber.progress_callback)

        progress_entries = [
            (call.args[1], call.args[2], call.args[3], call.args[4])
            for call in logger_mock.info.call_args_list
            if call.args and call.args[0] == "[%s] %s%% | %s | %s"
        ]
        self.assertEqual(
            progress_entries,
            [
                ("demo.m4a", 10, "processing_started", "File is stable. Starting analysis."),
                ("demo.m4a", 20, "transcribing", "Transcribing audio with faster-whisper."),
                ("demo.m4a", 55, "transcription_complete", "Collected 1 transcript segments."),
                ("demo.m4a", 75, "diarization_skipped", "Diarization disabled."),
                ("demo.m4a", 85, "summarizing", "Generating summary with Ollama."),
                ("demo.m4a", 95, "writing_output", "Writing markdown output."),
                ("demo.m4a", 100, "completed", "Saved markdown to demo.md."),
            ],
        )


if __name__ == "__main__":
    unittest.main()
