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


class _FakeDiarizer:
    def __init__(self, speaker_turns: list[object] | None = None, *, error: Exception | None = None) -> None:
        self.speaker_turns = speaker_turns or []
        self.error = error

    def diarize(self, audio_path: Path) -> list[object]:
        if self.error is not None:
            raise self.error
        return self.speaker_turns


class TranscriberTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_diarizer = _FakeDiarizer()
        self.create_diarization_support_patcher = patch(
            "meeting_summary.transcriber._create_diarization_support",
            return_value=(
                self.fake_diarizer,
                lambda utterances, speaker_turns: utterances,
                RuntimeError,
            ),
        )
        self.create_diarization_support_mock = self.create_diarization_support_patcher.start()
        self.addCleanup(self.create_diarization_support_patcher.stop)

    def test_transcriber_logs_guidance_for_heavy_cpu_runtime(self) -> None:
        init_calls: list[tuple[str, str, str]] = []

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            with self.assertLogs("meeting_summary.transcriber", level="WARNING") as captured_logs:
                Transcriber(
                    model_name="large-v3",
                    device="cpu",
                )

        self.assertEqual(init_calls, [("large-v3", "cpu", "int8")])
        self.assertIn("Long recordings can stay at 20%", captured_logs.output[0])
        self.assertIn("resource-heavy", captured_logs.output[1])

    def test_transcriber_warns_when_cpu_uses_default_compute_type(self) -> None:
        init_calls: list[tuple[str, str, str]] = []

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            with self.assertLogs("meeting_summary.transcriber", level="WARNING") as captured_logs:
                Transcriber(
                    model_name="medium",
                    device="cpu",
                    compute_type="default",
                )

        self.assertEqual(init_calls, [("medium", "cpu", "default")])
        self.assertIn("compute_type=default", captured_logs.output[0])

    def test_transcriber_initializes_diarization_support(self) -> None:
        init_calls: list[tuple[str, str, str]] = []

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)

        with patch.dict("sys.modules", {"faster_whisper": fake_faster_whisper}):
            with self.assertLogs("meeting_summary.transcriber", level="WARNING") as captured_logs:
                Transcriber(model_name="large-v3", device="cpu")

        self.assertEqual(init_calls, [("large-v3", "cpu", "int8")])
        self.assertIn("Long recordings can stay at 20%", captured_logs.output[0])
        self.create_diarization_support_mock.assert_called_once()

    def test_transcriber_fails_fast_when_diarization_dependency_is_missing(self) -> None:
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
                with self.assertRaisesRegex(RuntimeError, "Diarization dependencies are missing"):
                    Transcriber(
                        model_name="large-v3",
                        device="cpu",
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
                side_effect=RuntimeError(
                    "Could not load `pyannote/speaker-diarization-community-1`."
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "speaker-diarization-community-1",
                ):
                    Transcriber(
                        model_name="large-v3",
                        device="cpu",
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
            segments=[_FakeSegment("Hello", 0.0, 1.0)],
            info=SimpleNamespace(language="en", duration=1.0),
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))

        with patch.dict(
            "sys.modules",
            {"faster_whisper": fake_faster_whisper, "torch": fake_torch},
        ):
            transcriber = Transcriber(model_name="large-v3", device="auto")
            result = transcriber.transcribe(Path("demo.wav"))

        self.assertEqual(init_calls, [("large-v3", "cuda", "float16")])
        self.assertEqual(result.language, "en")

    def test_transcribe_uses_language_and_initial_prompt_when_provided(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Привет", 0.0, 0.5)],
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
            transcriber = Transcriber(
                model_name="large-v3",
                device="auto",
                language="ru",
                initial_prompt="Компания OpenAI, Ollama",
                beam_size=7,
            )
            result = transcriber.transcribe(Path("demo.m4a"))

        self.assertEqual(result.transcript, "Привет")
        self.assertEqual(
            fake_model.calls[0],
            {
                "audio_path": "demo.m4a",
                "language": "ru",
                "task": "transcribe",
                "temperature": 0.0,
                "condition_on_previous_text": True,
                "initial_prompt": "Компания OpenAI, Ollama",
                "vad_filter": True,
                "beam_size": 7,
            },
        )

    def test_transcribe_builds_initial_prompt_from_terms_when_prompt_is_missing(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Привет", 0.0, 0.5)],
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
            transcriber = Transcriber(
                model_name="large-v3",
                device="auto",
                terms=("OpenAI", "Ollama", "OpenAI"),
            )
            transcriber.transcribe(Path("demo.m4a"))

        self.assertEqual(fake_model.calls[0]["initial_prompt"], "OpenAI, Ollama")

    def test_transcribe_does_not_set_best_of_when_temperature_is_zero(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Привет", 0.0, 0.5)],
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
            transcriber = Transcriber(
                model_name="large-v3",
                device="auto",
                best_of=9,
                temperature=0.0,
            )
            transcriber.transcribe(Path("demo.m4a"))

        self.assertNotIn("best_of", fake_model.calls[0])

    def test_transcribe_sets_best_of_when_temperature_is_non_zero(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Привет", 0.0, 0.5)],
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
            transcriber = Transcriber(
                model_name="large-v3",
                device="auto",
                best_of=9,
                temperature=0.2,
            )
            transcriber.transcribe(Path("demo.m4a"))

        self.assertEqual(fake_model.calls[0]["best_of"], 9)

    def test_transcribe_reports_progress_during_whisper_processing(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            info=SimpleNamespace(language="ru", duration=300.0),
            segments=[
                _FakeSegment("один", 0.0, 60.0),
                _FakeSegment("два", 60.0, 150.0),
                _FakeSegment("три", 150.0, 299.0),
            ],
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        progress_events: list[tuple[str, int, str]] = []

        with patch.dict(
            "sys.modules",
            {"faster_whisper": fake_faster_whisper, "torch": fake_torch},
        ):
            transcriber = Transcriber(model_name="large-v3", device="auto")
            transcriber.transcribe(
                Path("demo.m4a"),
                progress_callback=lambda stage, percent, message: progress_events.append(
                    (stage, percent, message)
                ),
            )

        progress_stages = [event[0] for event in progress_events]
        self.assertIn("transcribing", progress_stages)
        self.assertIn("transcribing_progress", progress_stages)
        self.assertIn("transcription_complete", progress_stages)
        self.assertIn("diarizing", progress_stages)
        self.assertIn("diarization_complete", progress_stages)
        transcribing_progress = [event for event in progress_events if event[0] == "transcribing_progress"]
        self.assertTrue(transcribing_progress)
        self.assertEqual(transcribing_progress[-1][1], 54)

    def test_transcribe_reports_fallback_progress_when_duration_is_unknown(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            info=SimpleNamespace(language="ru", duration=None),
            segments=[_FakeSegment(f"сегмент {index}", index, index + 1.0) for index in range(26)],
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        progress_events: list[tuple[str, int, str]] = []

        with patch.dict(
            "sys.modules",
            {"faster_whisper": fake_faster_whisper, "torch": fake_torch},
        ):
            transcriber = Transcriber(model_name="large-v3", device="auto")
            transcriber.transcribe(
                Path("demo.m4a"),
                progress_callback=lambda stage, percent, message: progress_events.append(
                    (stage, percent, message)
                ),
            )

        transcribing_progress = [event for event in progress_events if event[0] == "transcribing_progress"]
        self.assertEqual(len(transcribing_progress), 1)
        self.assertEqual(transcribing_progress[0][1], 23)
        self.assertIn("25 transcript segments", transcribing_progress[0][2])

    def test_transcribe_falls_back_to_utterance_duration_when_info_has_none(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            info=SimpleNamespace(language="ru", duration=None),
            segments=[
                _FakeSegment("один", 0.0, 1.25),
                _FakeSegment("два", 1.25, 3.0),
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

        self.assertEqual(result.duration_seconds, 3.0)

    def test_transcribe_raises_for_empty_transcript(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("   ", 0.0, 1.0)],
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
            with self.assertRaisesRegex(RuntimeError, "is empty"):
                transcriber.transcribe(Path("demo.m4a"))

    def test_transcribe_raises_when_diarization_fails(self) -> None:
        init_calls: list[tuple[str, str, str]] = []
        fake_model = _FakeModel(
            init_calls,
            segments=[_FakeSegment("Привет", 0.0, 1.0)],
        )

        class _FakeWhisperModel:
            def __init__(self, name: str, device: str, compute_type: str) -> None:
                init_calls.append((name, device, compute_type))

            def transcribe(self, audio_path: str, **kwargs: object):
                return fake_model.transcribe(audio_path, **kwargs)

        fake_faster_whisper = SimpleNamespace(WhisperModel=_FakeWhisperModel)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        failing_diarizer = _FakeDiarizer(error=RuntimeError("boom"))

        with patch.dict(
            "sys.modules",
            {"faster_whisper": fake_faster_whisper, "torch": fake_torch},
        ):
            with patch(
                "meeting_summary.transcriber._create_diarization_support",
                return_value=(failing_diarizer, lambda utterances, _: utterances, RuntimeError),
            ):
                transcriber = Transcriber(model_name="large-v3", device="auto")
                with self.assertRaisesRegex(RuntimeError, "Diarization failed for demo.m4a"):
                    transcriber.transcribe(Path("demo.m4a"))


if __name__ == "__main__":
    unittest.main()
