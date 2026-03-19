from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from meeting_summary.diarization import (
    PyannoteDiarizer,
    SpeakerTurn,
    _load_audio,
    _load_pipeline,
    assign_speakers,
)
from meeting_summary.models import TranscriptUtterance


class _FakePipelineV3:
    @classmethod
    def from_pretrained(cls, checkpoint, use_auth_token=None):  # noqa: ANN001
        return checkpoint, use_auth_token


class _FakePipelineV4:
    @classmethod
    def from_pretrained(cls, checkpoint, token=None):  # noqa: ANN001
        return checkpoint, token


class _FakeSegment:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class _FakeAnnotation:
    def __init__(self, turns: list[tuple[float, float, str]]) -> None:
        self.turns = turns

    def itertracks(self, yield_label: bool = False):
        for start, end, speaker in self.turns:
            yield _FakeSegment(start, end), None, speaker


class _FakeOutput:
    def __init__(
        self,
        *,
        exclusive_speaker_diarization: _FakeAnnotation | None = None,
        speaker_diarization: _FakeAnnotation | None = None,
    ) -> None:
        self.exclusive_speaker_diarization = exclusive_speaker_diarization
        self.speaker_diarization = speaker_diarization


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

    def test_diarize_prefers_exclusive_speaker_diarization(self) -> None:
        diarizer = PyannoteDiarizer.__new__(PyannoteDiarizer)
        diarizer.pipeline = lambda _: _FakeOutput(
            exclusive_speaker_diarization=_FakeAnnotation([(0.0, 1.0, "SPEAKER_00")]),
            speaker_diarization=_FakeAnnotation([(1.0, 2.0, "SPEAKER_99")]),
        )

        with patch(
            "meeting_summary.diarization._load_audio",
            return_value={"waveform": object(), "sample_rate": 16000},
        ):
            turns = diarizer.diarize(audio_path=Path("demo.m4a"))

        self.assertEqual(turns, [SpeakerTurn("SPEAKER_00", 0.0, 1.0)])

    def test_diarize_falls_back_to_speaker_diarization_attribute(self) -> None:
        diarizer = PyannoteDiarizer.__new__(PyannoteDiarizer)
        diarizer.pipeline = lambda _: _FakeOutput(
            speaker_diarization=_FakeAnnotation([(2.0, 3.0, "SPEAKER_01")]),
        )

        with patch(
            "meeting_summary.diarization._load_audio",
            return_value={"waveform": object(), "sample_rate": 16000},
        ):
            turns = diarizer.diarize(audio_path=Path("demo.m4a"))

        self.assertEqual(turns, [SpeakerTurn("SPEAKER_01", 2.0, 3.0)])

    def test_diarize_falls_back_to_direct_annotation_output(self) -> None:
        diarizer = PyannoteDiarizer.__new__(PyannoteDiarizer)
        diarizer.pipeline = lambda _: _FakeAnnotation([(4.0, 5.5, "SPEAKER_02")])

        with patch(
            "meeting_summary.diarization._load_audio",
            return_value={"waveform": object(), "sample_rate": 16000},
        ):
            turns = diarizer.diarize(audio_path=Path("demo.m4a"))

        self.assertEqual(turns, [SpeakerTurn("SPEAKER_02", 4.0, 5.5)])

    def test_load_pipeline_supports_v3_use_auth_token_signature(self) -> None:
        pipeline = _load_pipeline(
            pipeline_cls=_FakePipelineV3,
            model_name="pyannote/speaker-diarization-3.1",
            auth_token="hf_test",
        )

        self.assertEqual(pipeline, ("pyannote/speaker-diarization-3.1", "hf_test"))

    def test_load_pipeline_supports_v4_token_signature(self) -> None:
        pipeline = _load_pipeline(
            pipeline_cls=_FakePipelineV4,
            model_name="pyannote/speaker-diarization-community-1",
            auth_token="hf_test",
        )

        self.assertEqual(pipeline, ("pyannote/speaker-diarization-community-1", "hf_test"))

    def test_load_audio_uses_torchaudio_when_available(self) -> None:
        expected_waveform = object()
        fake_torchaudio = SimpleNamespace(load=lambda _: (expected_waveform, 44100))

        with patch.dict("sys.modules", {"torchaudio": fake_torchaudio, "torch": SimpleNamespace()}):
            audio = _load_audio(Path("demo.wav"))

        self.assertIs(audio["waveform"], expected_waveform)
        self.assertEqual(audio["sample_rate"], 44100)

    def test_load_audio_falls_back_to_whisper_decode(self) -> None:
        fake_tensor = object()

        class _FakeTorch:
            @staticmethod
            def from_numpy(value):  # noqa: ANN001
                class _Tensor:
                    def __init__(self, payload):  # noqa: ANN001
                        self.payload = payload

                    def unsqueeze(self, dim):  # noqa: ANN001
                        return fake_tensor if dim == 0 else None

                return _Tensor(value)

        fake_torchaudio = SimpleNamespace(
            load=lambda _: (_ for _ in ()).throw(RuntimeError("Format not recognised"))
        )
        fake_whisper = SimpleNamespace(load_audio=lambda _: ["pcm"])

        with patch.dict(
            "sys.modules",
            {
                "torchaudio": fake_torchaudio,
                "torch": _FakeTorch(),
                "whisper": fake_whisper,
            },
        ):
            audio = _load_audio(Path("demo.m4a"))

        self.assertIs(audio["waveform"], fake_tensor)
        self.assertEqual(audio["sample_rate"], 16000)


if __name__ == "__main__":
    unittest.main()
