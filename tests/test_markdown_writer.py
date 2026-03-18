from __future__ import annotations

import unittest
from pathlib import Path

from meeting_summary.markdown_writer import build_markdown, markdown_path_for
from meeting_summary.models import CallSummary, TranscriptionResult


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


if __name__ == "__main__":
    unittest.main()
