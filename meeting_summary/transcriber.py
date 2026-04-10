from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Callable, Protocol

from meeting_summary.models import TranscriptUtterance, TranscriptionResult

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[str, int, str], None]

_TRANSCRIPTION_PERCENT_START = 20
_TRANSCRIPTION_PERCENT_END = 55
_TRANSCRIPTION_PROGRESS_STEP = 3
_TRANSCRIPTION_HEARTBEAT_SECONDS = 15.0
_TRANSCRIPTION_SEGMENT_HEARTBEAT = 25
_CPU_HEAVY_MODELS = {"large-v3"}


class DiarizationConfigurationError(RuntimeError):
    """Raised when diarization is enabled but runtime dependencies are misconfigured."""


class _Diarizer(Protocol):
    def diarize(self, audio_path: Path) -> list[object]:
        ...


AssignSpeakersCallback = Callable[
    [list[TranscriptUtterance], list[object]],
    list[TranscriptUtterance],
]


class Transcriber:
    def __init__(
        self,
        model_name: str,
        device: str,
        compute_type: str = "auto",
        language: str | None = None,
        initial_prompt: str | None = None,
        terms: tuple[str, ...] = (),
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        diarization_auth_token: str | None = None,
        diarization_device: str = "auto",
    ) -> None:
        from faster_whisper import WhisperModel

        self.model_name = model_name
        self.device = _resolve_whisper_device(device)
        self.compute_type = _resolve_compute_type(self.device, compute_type)
        self.language = language
        self.terms = _normalize_terms(terms)
        self.initial_prompt = _resolve_initial_prompt(initial_prompt, self.terms)
        self.beam_size = beam_size
        self.best_of = best_of
        self.temperature = temperature
        self.vad_filter = vad_filter
        self.model = WhisperModel(
            model_name,
            device=self.device,
            compute_type=self.compute_type,
        )
        LOGGER.info(
            "Loaded faster-whisper model '%s' with device=%s, compute_type=%s, language=%s, beam_size=%s, best_of=%s, temperature=%s, vad_filter=%s, glossary_terms=%s.",
            model_name,
            self.device,
            self.compute_type,
            self.language or "auto",
            self.beam_size,
            self.best_of,
            self.temperature,
            self.vad_filter,
            len(self.terms),
        )
        self.diarizer: _Diarizer | None = None
        self._assign_speakers: AssignSpeakersCallback | None = None
        self._diarization_skipped_error: type[Exception] | None = None
        try:
            (
                self.diarizer,
                self._assign_speakers,
                self._diarization_skipped_error,
            ) = _create_diarization_support(
                auth_token=diarization_auth_token,
                device=diarization_device,
            )
        except ModuleNotFoundError as exc:
            raise DiarizationConfigurationError(
                "Diarization dependencies are missing "
                f"({exc.name or str(exc)}). Reinstall the project in the active virtual "
                "environment before starting the service."
            ) from exc
        except Exception as exc:
            raise DiarizationConfigurationError(str(exc)) from exc
        self._log_runtime_guidance()

    def transcribe(
        self,
        audio_path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> TranscriptionResult:
        _report_progress(
            progress_callback,
            "transcribing",
            20,
            "Transcribing audio with faster-whisper.",
        )
        utterances, info = self._transcribe_segments(
            audio_path,
            progress_callback=progress_callback,
        )
        _report_progress(
            progress_callback,
            "transcription_complete",
            55,
            f"Collected {len(utterances)} transcript segments.",
        )

        _report_progress(
            progress_callback,
            "diarizing",
            60,
            "Running speaker diarization.",
        )
        try:
            speaker_turns = self.diarizer.diarize(audio_path)
            utterances = self._assign_speakers(utterances, speaker_turns)
            speaker_count = len({turn.speaker for turn in speaker_turns})
            _report_progress(
                progress_callback,
                "diarization_complete",
                75,
                f"Diarization finished with {speaker_count} speakers.",
            )
        except Exception:
            LOGGER.exception("Failed to diarize %s.", audio_path.name)
            raise RuntimeError(f"Diarization failed for {audio_path.name}.") from None

        transcript = " ".join(utterance.text for utterance in utterances if utterance.text.strip())
        if not transcript:
            raise RuntimeError(f"Transcription for {audio_path.name} is empty.")

        detected_language = getattr(info, "language", None)
        duration_seconds = getattr(info, "duration", None) or _transcript_duration_seconds(
            utterances
        )

        return TranscriptionResult(
            source_path=audio_path,
            transcript=transcript,
            language=detected_language,
            duration_seconds=duration_seconds,
            utterances=utterances,
        )

    def _transcribe_segments(
        self,
        audio_path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[list[TranscriptUtterance], object]:
        segments, info = self.model.transcribe(
            str(audio_path),
            **self._build_decode_options(),
        )
        progress_reporter = _TranscriptionProgressReporter(
            progress_callback=progress_callback,
            total_duration_seconds=getattr(info, "duration", None),
        )
        utterances: list[TranscriptUtterance] = []
        for segment_index, segment in enumerate(segments, start=1):
            progress_reporter.on_segment(
                segment_end_seconds=segment.end,
                collected_segments=segment_index,
            )
            text = segment.text.strip()
            if not text:
                continue
            utterances.append(
                TranscriptUtterance(
                    text=text,
                    start_seconds=float(segment.start) if segment.start is not None else None,
                    end_seconds=float(segment.end) if segment.end is not None else None,
                )
            )
        return utterances, info

    def _build_decode_options(self) -> dict[str, str | int | float | bool | None]:
        decode_options: dict[str, str | int | float | bool | None] = {
            "language": self.language,
            "task": "transcribe",
            "temperature": self.temperature,
            "condition_on_previous_text": True,
            "initial_prompt": self.initial_prompt,
            "vad_filter": self.vad_filter,
            "beam_size": self.beam_size,
        }
        if self.temperature != 0:
            decode_options["best_of"] = self.best_of

        return decode_options

    def _log_runtime_guidance(self) -> None:
        if self.device == "cpu" and self.model_name in _CPU_HEAVY_MODELS:
            LOGGER.warning(
                "Model '%s' is running on CPU. Long recordings can stay at 20%% until the first "
                "segments are decoded. For a faster native macOS default, prefer `WHISPER_MODEL=medium`.",
                self.model_name,
            )

        if self.device == "cpu" and self.compute_type == "default":
            LOGGER.warning(
                "CPU transcription is using compute_type=default. This is heavier than the "
                "recommended CPU path. Prefer `WHISPER_COMPUTE_TYPE=auto` or `int8`."
            )

        if self.device == "cpu" and self.model_name in _CPU_HEAVY_MODELS:
            LOGGER.warning(
                "Current runtime is resource-heavy: model='%s', device=cpu, diarization enabled. "
                "On Apple Silicon machines with 16 GB RAM, prefer `WHISPER_MODEL=medium` for routine runs.",
                self.model_name,
            )


class _TranscriptionProgressReporter:
    def __init__(
        self,
        progress_callback: ProgressCallback | None,
        total_duration_seconds: float | None,
    ) -> None:
        self.progress_callback = progress_callback
        self.total_duration_seconds = (
            float(total_duration_seconds)
            if total_duration_seconds is not None and total_duration_seconds > 0
            else None
        )
        self._last_percent = _TRANSCRIPTION_PERCENT_START
        self._last_reported_seconds = 0.0
        self._last_reported_segments = 0
        self._last_report_monotonic = time.monotonic()

    def on_segment(self, segment_end_seconds: float | None, collected_segments: int) -> None:
        if self.progress_callback is None:
            return

        now = time.monotonic()
        if self.total_duration_seconds is not None and segment_end_seconds is not None:
            processed_seconds = min(max(float(segment_end_seconds), 0.0), self.total_duration_seconds)
            if processed_seconds >= self.total_duration_seconds:
                return

            percent = _transcription_progress_percent(
                processed_seconds=processed_seconds,
                total_duration_seconds=self.total_duration_seconds,
            )
            percent_advanced = percent >= self._last_percent + _TRANSCRIPTION_PROGRESS_STEP
            heartbeat_due = (
                now - self._last_report_monotonic >= _TRANSCRIPTION_HEARTBEAT_SECONDS
                and processed_seconds > self._last_reported_seconds
            )
            if not percent_advanced and not heartbeat_due:
                return

            _report_progress(
                self.progress_callback,
                "transcribing_progress",
                percent,
                _format_duration_progress_message(processed_seconds, self.total_duration_seconds),
            )
            self._last_percent = max(self._last_percent, percent)
            self._last_reported_seconds = processed_seconds
            self._last_reported_segments = collected_segments
            self._last_report_monotonic = now
            return

        segments_advanced = (
            collected_segments - self._last_reported_segments >= _TRANSCRIPTION_SEGMENT_HEARTBEAT
        )
        heartbeat_due = (
            now - self._last_report_monotonic >= _TRANSCRIPTION_HEARTBEAT_SECONDS
            and collected_segments > self._last_reported_segments
        )
        if not segments_advanced and not heartbeat_due:
            return

        percent = min(
            _TRANSCRIPTION_PERCENT_END - 1,
            self._last_percent + _TRANSCRIPTION_PROGRESS_STEP,
        )
        _report_progress(
            self.progress_callback,
            "transcribing_progress",
            percent,
            f"Processed {collected_segments} transcript segments.",
        )
        self._last_percent = percent
        self._last_reported_segments = collected_segments
        self._last_report_monotonic = now


def _resolve_whisper_device(device: str) -> str:
    if device != "auto":
        return device

    try:
        import torch
    except ModuleNotFoundError:
        return "cpu"

    return "cuda" if torch.cuda.is_available() else "cpu"


def _resolve_compute_type(device: str, compute_type: str) -> str:
    if compute_type != "auto":
        return compute_type

    return "float16" if device == "cuda" else "int8"


def _resolve_initial_prompt(
    initial_prompt: str | None,
    terms: tuple[str, ...],
) -> str | None:
    if initial_prompt:
        stripped = initial_prompt.strip()
        return stripped or None

    if not terms:
        return None

    return ", ".join(terms)


def _normalize_terms(terms: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_term in terms:
        term = raw_term.strip()
        if not term or term in seen:
            continue
        seen.add(term)
        normalized.append(term)
    return tuple(normalized)


def _create_diarization_support(
    auth_token: str | None,
    device: str,
) -> tuple[_Diarizer, AssignSpeakersCallback, type[Exception]]:
    from meeting_summary.diarization import (
        DiarizationSkipped,
        PyannoteDiarizer,
        assign_speakers,
    )

    diarizer = PyannoteDiarizer(auth_token=auth_token, device=device)
    return diarizer, assign_speakers, DiarizationSkipped


def _report_progress(
    progress_callback: ProgressCallback | None,
    stage: str,
    percent: int,
    message: str,
) -> None:
    if progress_callback is None:
        return
    progress_callback(stage, percent, message)


def _transcription_progress_percent(
    *,
    processed_seconds: float,
    total_duration_seconds: float,
) -> int:
    if total_duration_seconds <= 0:
        return _TRANSCRIPTION_PERCENT_START

    span = _TRANSCRIPTION_PERCENT_END - _TRANSCRIPTION_PERCENT_START
    completion_ratio = min(max(processed_seconds / total_duration_seconds, 0.0), 1.0)
    percent = _TRANSCRIPTION_PERCENT_START + int(span * completion_ratio)
    return min(max(percent, _TRANSCRIPTION_PERCENT_START), _TRANSCRIPTION_PERCENT_END - 1)


def _format_duration_progress_message(
    processed_seconds: float,
    total_duration_seconds: float,
) -> str:
    processed_minutes = processed_seconds / 60
    total_minutes = total_duration_seconds / 60
    return (
        f"Processed {processed_minutes:.1f} / {total_minutes:.1f} min of audio."
    )


def _transcript_duration_seconds(utterances: list[TranscriptUtterance]) -> float | None:
    max_end_seconds = max(
        (
            utterance.end_seconds
            for utterance in utterances
            if utterance.end_seconds is not None
        ),
        default=None,
    )
    return float(max_end_seconds) if max_end_seconds is not None else None
