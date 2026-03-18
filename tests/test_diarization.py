from __future__ import annotations

import unittest

from meeting_summary.diarization import SpeakerTurn, assign_speakers
from meeting_summary.models import TranscriptUtterance


class DiarizationTests(unittest.TestCase):
    def test_assign_speakers_uses_largest_overlap(self) -> None:
        segments = [
            TranscriptUtterance(
                text="Первый фрагмент",
                start_seconds=0.0,
                end_seconds=4.0,
            ),
            TranscriptUtterance(
                text="Второй фрагмент",
                start_seconds=4.0,
                end_seconds=7.0,
            ),
        ]
        speaker_turns = [
            SpeakerTurn(speaker="Speaker 1", start_seconds=0.0, end_seconds=3.5),
            SpeakerTurn(speaker="Speaker 2", start_seconds=3.5, end_seconds=7.5),
        ]

        utterances = assign_speakers(segments, speaker_turns)

        self.assertEqual(utterances[0].speaker, "Speaker 1")
        self.assertEqual(utterances[1].speaker, "Speaker 2")

    def test_assign_speakers_keeps_plain_segments_without_turns(self) -> None:
        segments = [
            TranscriptUtterance(
                text="Фрагмент",
                start_seconds=0.0,
                end_seconds=2.0,
            )
        ]

        utterances = assign_speakers(segments, [])

        self.assertIsNone(utterances[0].speaker)
        self.assertEqual(utterances[0].text, "Фрагмент")


if __name__ == "__main__":
    unittest.main()
