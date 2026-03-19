from __future__ import annotations

import unittest
from pathlib import Path

from meeting_summary.markdown_writer import build_markdown, markdown_path_for
from meeting_summary.models import CallSummary, TranscriptUtterance, TranscriptionResult


class MarkdownWriterTests(unittest.TestCase):
    def test_markdown_path_changes_suffix_to_md(self) -> None:
        self.assertEqual(markdown_path_for(Path("calls/demo.m4a")), Path("calls/demo.md"))

    def test_build_markdown_contains_summary_and_transcript(self) -> None:
        transcription = TranscriptionResult(
            source_path=Path("calls/demo.m4a"),
            transcript="Полный текст разговора",
            language="ru",
            duration_seconds=12.3,
        )
        summary = CallSummary(content="## Кратко\n\nГлавная мысль")

        markdown = build_markdown(transcription=transcription, summary=summary)

        self.assertIn("# demo.m4a", markdown)
        self.assertIn("## Summary", markdown)
        self.assertIn("## Transcript", markdown)
        self.assertIn("Главная мысль", markdown)
        self.assertIn("Полный текст разговора", markdown)
        self.assertIn("- Speakers detected: no", markdown)

    def test_build_markdown_formats_speaker_utterances(self) -> None:
        transcription = TranscriptionResult(
            source_path=Path("calls/demo.m4a"),
            transcript="Добрый день Давайте начнем",
            language="ru",
            duration_seconds=12.3,
            utterances=[
                TranscriptUtterance(
                    text="Добрый день",
                    speaker="Speaker 1",
                    start_seconds=0.0,
                    end_seconds=1.9,
                ),
                TranscriptUtterance(
                    text="Давайте начнем",
                    speaker="Speaker 2",
                    start_seconds=2.0,
                    end_seconds=4.2,
                ),
            ],
        )
        summary = CallSummary(content="## Кратко\n\nГлавная мысль")

        markdown = build_markdown(transcription=transcription, summary=summary)

        self.assertIn("- Speakers detected: yes", markdown)
        self.assertIn("[00:00-00:01] Speaker 1: Добрый день", markdown)
        self.assertIn("[00:02-00:04] Speaker 2: Давайте начнем", markdown)


if __name__ == "__main__":
    unittest.main()
