from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from meeting_summary.diarization import DiarizationSkipped, PyannoteDiarizer, assign_speakers
from meeting_summary.models import TranscriptUtterance, TranscriptionResult

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[str, int, str], None]


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
        enable_diarization: bool = False,
        diarization_auth_token: str | None = None,
        diarization_device: str = "auto",
    ) -> None:
        from faster_whisper import WhisperModel

        self.device = _resolve_whisper_device(device)
        self.compute_type = _resolve_compute_type(self.device, compute_type)
        self.language = language
        self.terms = tuple(term.strip() for term in terms if term.strip())
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
        self.diarizer: PyannoteDiarizer | None = None
        if enable_diarization:
            try:
                self.diarizer = PyannoteDiarizer(
                    auth_token=diarization_auth_token,
                    device=diarization_device,
                )
            except Exception:
                LOGGER.warning(
                    "Failed to initialize pyannote diarization. Falling back to plain transcript mode.",
                    exc_info=True,
                )

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
        utterances, info = self._transcribe_segments(audio_path)
        _report_progress(
            progress_callback,
            "transcription_complete",
            55,
            f"Collected {len(utterances)} transcript segments.",
        )

        if self.diarizer is not None:
            _report_progress(
                progress_callback,
                "diarizing",
                60,
                "Running speaker diarization.",
            )
            try:
                speaker_turns = self.diarizer.diarize(audio_path)
                utterances = assign_speakers(utterances, speaker_turns)
                speaker_count = len({turn.speaker for turn in speaker_turns})
                _report_progress(
                    progress_callback,
                    "diarization_complete",
                    75,
                    f"Diarization finished with {speaker_count} speakers.",
                )
            except DiarizationSkipped as exc:
                LOGGER.info("Skipping diarization for %s: %s", audio_path.name, exc)
                _report_progress(
                    progress_callback,
                    "diarization_skipped",
                    75,
                    str(exc),
                )
            except Exception:
                LOGGER.warning(
                    "Failed to diarize %s. Falling back to plain transcript mode.",
                    audio_path.name,
                    exc_info=True,
                )
                _report_progress(
                    progress_callback,
                    "diarization_skipped",
                    75,
                    "Diarization failed; continuing without speaker labels.",
                )
        else:
            _report_progress(
                progress_callback,
                "diarization_skipped",
                75,
                "Diarization disabled.",
            )

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
    ) -> tuple[list[TranscriptUtterance], object]:
        segments, info = self.model.transcribe(
            str(audio_path),
            **self._build_decode_options(),
        )
        utterances = [
            TranscriptUtterance(
                text=segment.text.strip(),
                start_seconds=float(segment.start) if segment.start is not None else None,
                end_seconds=float(segment.end) if segment.end is not None else None,
            )
            for segment in segments
            if segment.text.strip()
        ]
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


def _resolve_whisper_device(device: str) -> str:
    if device != "auto":
        return device

    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _resolve_compute_type(device: str, compute_type: str) -> str:
    if compute_type != "auto":
        return compute_type

    if device == "cuda":
        return "float16"

    return "int8"


def _transcript_duration_seconds(utterances: list[TranscriptUtterance]) -> float | None:
    end_times = [
        utterance.end_seconds for utterance in utterances if utterance.end_seconds is not None
    ]
    if not end_times:
        return None

    return max(end_times)


def _resolve_initial_prompt(initial_prompt: str | None, terms: tuple[str, ...]) -> str | None:
    if initial_prompt is not None and initial_prompt.strip():
        return initial_prompt.strip()

    if not terms:
        return None

    return ", ".join(terms)


def _report_progress(
    progress_callback: ProgressCallback | None,
    stage: str,
    percent: int,
    message: str,
) -> None:
    if progress_callback is None:
        return

    progress_callback(stage, percent, message)
