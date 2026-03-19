from __future__ import annotations

import logging
from pathlib import Path

from meeting_summary.diarization import PyannoteDiarizer, assign_speakers
from meeting_summary.models import TranscriptUtterance, TranscriptionResult

LOGGER = logging.getLogger(__name__)


class Transcriber:
    def __init__(
        self,
        model_name: str,
        device: str,
        enable_diarization: bool = False,
        diarization_auth_token: str | None = None,
        diarization_device: str = "auto",
    ) -> None:
        import whisper

        self.device = _resolve_whisper_device(device)
        self.model = whisper.load_model(model_name, device=self.device)
        LOGGER.info(
            "Loaded openai-whisper model '%s' with device=%s.",
            model_name,
            self.device,
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

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        result = self.model.transcribe(
            str(audio_path),
            fp16=self.device == "cuda",
        )
        utterances = [
            TranscriptUtterance(
                text=segment["text"].strip(),
                start_seconds=float(segment["start"]) if segment.get("start") is not None else None,
                end_seconds=float(segment["end"]) if segment.get("end") is not None else None,
            )
            for segment in result.get("segments", [])
            if segment.get("text", "").strip()
        ]

        if self.diarizer is not None:
            try:
                speaker_turns = self.diarizer.diarize(audio_path)
                utterances = assign_speakers(utterances, speaker_turns)
            except Exception:
                LOGGER.warning(
                    "Failed to diarize %s. Falling back to plain transcript mode.",
                    audio_path.name,
                    exc_info=True,
                )

        transcript = " ".join(utterance.text for utterance in utterances if utterance.text.strip())
        if not transcript:
            raise RuntimeError(f"Transcription for {audio_path.name} is empty.")

        return TranscriptionResult(
            source_path=audio_path,
            transcript=transcript,
            language=result.get("language"),
            duration_seconds=_transcript_duration_seconds(utterances),
            utterances=utterances,
        )


def _resolve_whisper_device(device: str) -> str:
    if device != "auto":
        return device

    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _transcript_duration_seconds(utterances: list[TranscriptUtterance]) -> float | None:
    end_times = [
        utterance.end_seconds for utterance in utterances if utterance.end_seconds is not None
    ]
    if not end_times:
        return None

    return max(end_times)
