from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from meeting_summary.transcriber import Transcriber


class _FakeSegment:
    def __init__(self, text: str, start: float | None, end: float | None) -> None:
        self.text = text
        self.start = start
        self.end = end


class _FakeModel:
    def __init__(
        self,
        init_calls: list[tuple[str, str, str]],
        *,
        info: object | None = None,
        segments: list[_FakeSegment] | None = None,
    ) -> None:
        self.init_calls = init_calls
        self.info = info or SimpleNamespace(language="ru", duration=2.75)
        self.segments = segments or []
        self.calls: list[dict[str, object]] = []

    def transcribe(self, audio_path: str, **kwargs: object):
        self.calls.append({"audio_path": audio_path, **kwargs})
        return iter(self.segments), self.info


class TranscriberTests(unittest.TestCase):
    def test_transcriber_does_not_initialize_diarization_when_disabled(self) -> None:
        init_calls: list[tuple[str, str, str]] = []

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            with patch(
                "meeting_summary.transcriber._create_diarization_support",
                side_effect=AssertionError("diarization helper should not be called"),
            ) as diarization_support_mock:
                Transcriber(model_name="large-v3", device="cpu", enable_diarization=False)

        self.assertEqual(init_calls, [("large-v3", "cpu", "int8")])
        diarization_support_mock.assert_not_called()

    def test_transcriber_fails_fast_when_diarization_extra_is_missing(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            with patch(
                "meeting_summary.transcriber._create_diarization_support",
                side_effect=ModuleNotFoundError("No module named 'pyannote.audio'"),
            ):
                with self.assertRaisesRegex(RuntimeError, "optional diarization dependencies are missing"):
                    transcriber = Transcriber(
                        model_name="large-v3",
                        device="cpu",
                        enable_diarization=True,
                    )

        self.assertEqual(init_calls, [("large-v3", "cpu", "int8")])

    def test_transcriber_fails_fast_when_diarization_pipeline_init_fails(self) -> None:
        init_calls: list[tuple[str, str, str]] = []

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            with patch(
                "meeting_summary.transcriber._create_diarization_support",
                side_effect=RuntimeError("401 Unauthorized"),
            ):
                with self.assertRaisesRegex(RuntimeError, "pyannote diarization failed to initialize"):
                    Transcriber(
                        model_name="large-v3",
                        device="cpu",
                        enable_diarization=True,
                        diarization_auth_token="hf_test",
                    )

        self.assertEqual(init_calls, [("large-v3", "cpu", "int8")])

    def test_transcribe_maps_faster_whisper_segments_to_result(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[
                _FakeSegment(" Привет ", 0.0, 1.25),
                _FakeSegment(" ", 1.25, 1.5),
                _FakeSegment("мир", 1.5, 2.75),
            ],
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))

        with patch.dict(
            "sys.modules",
            {"faster_whisper": fake_faster_whisper, "torch": fake_torch},
        ):
            transcriber = Transcriber(model_name="large-v3", device="auto")
            result = transcriber.transcribe(Path("demo.m4a"))

        self.assertEqual(init_calls, [("large-v3", "cpu", "int8")])
        self.assertEqual(result.transcript, "Привет мир")
        self.assertEqual(result.language, "ru")
        self.assertEqual(result.duration_seconds, 2.75)
        self.assertEqual(
            fake_model.calls,
            [
                {
                    "audio_path": "demo.m4a",
                    "language": None,
                    "task": "transcribe",
                    "temperature": 0.0,
                    "condition_on_previous_text": True,
                    "initial_prompt": None,
                    "vad_filter": True,
                    "beam_size": 5,
                }
            ],
        )

    def test_transcribe_uses_float16_compute_type_on_cuda_auto(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("тест", 0.0, 1.0)],
            info=SimpleNamespace(language="ru", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(model_name="large-v3", device="cuda")
            transcriber.transcribe(Path("gpu-demo.m4a"))

        self.assertEqual(init_calls, [("large-v3", "cuda", "float16")])

    def test_transcribe_reports_intermediate_progress_when_duration_is_known(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[
                _FakeSegment("первый", 0.0, 2.0),
                _FakeSegment("второй", 2.0, 5.0),
                _FakeSegment("третий", 5.0, 10.0),
            ],
            info=SimpleNamespace(language="ru", duration=10.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        progress_events: list[tuple[str, int, str]] = []

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(model_name="large-v3", device="cpu")
            transcriber.transcribe(
                Path("progress-demo.m4a"),
                progress_callback=lambda stage, percent, message: progress_events.append(
                    (stage, percent, message)
                ),
            )

        self.assertEqual(
            progress_events,
            [
                ("transcribing", 20, "Transcribing audio with faster-whisper."),
                ("transcribing_progress", 27, "Processed 0.0 / 0.2 min of audio."),
                ("transcribing_progress", 37, "Processed 0.1 / 0.2 min of audio."),
                ("transcription_complete", 55, "Collected 3 transcript segments."),
                ("diarization_skipped", 75, "Diarization disabled."),
            ],
        )

    def test_transcribe_reports_safe_heartbeat_without_total_duration(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        segments = [
            _FakeSegment(f"сегмент {index}", float(index), float(index + 1))
            for index in range(25)
        ]
        fake_model = _FakeModel(
            init_calls,
            segments=segments,
            info=SimpleNamespace(language="ru", duration=None),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        progress_events: list[tuple[str, int, str]] = []

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(model_name="large-v3", device="cpu")
            transcriber.transcribe(
                Path("progress-fallback.m4a"),
                progress_callback=lambda stage, percent, message: progress_events.append(
                    (stage, percent, message)
                ),
            )

        self.assertIn(
            (
                "transcribing_progress",
                20,
                "Collected 25 transcript segments so far.",
            ),
            progress_events,
        )

    def test_transcribe_passes_quality_overrides_and_vad(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("backend deploy", 0.0, 1.0)],
            info=SimpleNamespace(language="ru", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(
                model_name="large-v3",
                device="cpu",
                compute_type="int8",
                language="ru",
                initial_prompt="Docker, GitHub, backend, deploy",
                beam_size=7,
                best_of=6,
                temperature=0.0,
                vad_filter=True,
            )
            transcriber.transcribe(Path("quality-demo.m4a"))

        self.assertEqual(
            fake_model.calls[0],
            {
                "audio_path": "quality-demo.m4a",
                "language": "ru",
                "task": "transcribe",
                "temperature": 0.0,
                "condition_on_previous_text": True,
                "initial_prompt": "Docker, GitHub, backend, deploy",
                "vad_filter": True,
                "beam_size": 7,
            },
        )

    def test_transcribe_builds_short_glossary_prompt_from_terms(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Docker deploy", 0.0, 1.0)],
            info=SimpleNamespace(language="ru", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(
                model_name="large-v3",
                device="cpu",
                language="ru",
                terms=("Docker", "GitHub", "API", "deploy"),
            )
            transcriber.transcribe(Path("glossary-demo.m4a"))

        self.assertEqual(fake_model.calls[0]["initial_prompt"], "Docker, GitHub, API, deploy")

    def test_explicit_initial_prompt_overrides_auto_glossary_terms(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Docker deploy", 0.0, 1.0)],
            info=SimpleNamespace(language="ru", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(
                model_name="large-v3",
                device="cpu",
                language="ru",
                initial_prompt="Custom prompt",
                terms=("Docker", "GitHub"),
            )
            transcriber.transcribe(Path("glossary-demo.m4a"))

        self.assertEqual(fake_model.calls[0]["initial_prompt"], "Custom prompt")

    def test_transcribe_uses_best_of_for_nonzero_temperature(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("qa check", 0.0, 1.0)],
            info=SimpleNamespace(language="ru", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(
                model_name="large-v3",
                device="cpu",
                language="ru",
                beam_size=7,
                best_of=6,
                temperature=0.2,
            )
            transcriber.transcribe(Path("sampling-demo.m4a"))

        self.assertEqual(fake_model.calls[0]["best_of"], 6)
        self.assertEqual(fake_model.calls[0]["temperature"], 0.2)
        self.assertEqual(fake_model.calls[0]["beam_size"], 7)

    def test_transcribe_raises_on_empty_transcript(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("   ", None, None)],
            info=SimpleNamespace(language="ru", duration=None),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(model_name="large-v3", device="cpu")

        with self.assertRaisesRegex(RuntimeError, "empty"):
            transcriber.transcribe(Path("empty.m4a"))

    def test_transcribe_reports_progress_stages(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("тест", 0.0, 1.0)],
            info=SimpleNamespace(language="ru", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        progress_events: list[tuple[str, int, str]] = []

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            transcriber = Transcriber(model_name="large-v3", device="cpu")
            transcriber.transcribe(
                Path("demo.m4a"),
                progress_callback=lambda stage, percent, message: progress_events.append(
                    (stage, percent, message)
                ),
            )

        self.assertEqual(
            progress_events,
            [
                ("transcribing", 20, "Transcribing audio with faster-whisper."),
                ("transcription_complete", 55, "Collected 1 transcript segments."),
                ("diarization_skipped", 75, "Diarization disabled."),
            ],
        )


if __name__ == "__main__":
    unittest.main()
