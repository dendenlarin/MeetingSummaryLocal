from __future__ import annotations

import logging
from pathlib import Path

from meeting_summary.diarization import PyannoteDiarizer, assign_speakers
from meeting_summary.models import TranscriptUtterance, TranscriptionResult

LOGGER = logging.getLogger(__name__)


class Transcriber:
    def __init__(
        self,
        model_size: str,
        device: str,
        compute_type: str,
        enable_diarization: bool = False,
        diarization_auth_token: str | None = None,
        diarization_device: str = "auto",
    ) -> None:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        LOGGER.info(
            "Loaded faster-whisper model '%s' with device=%s compute_type=%s.",
            model_size,
            device,
            compute_type,
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
        segments, info = self.model.transcribe(str(audio_path), vad_filter=True)
        utterances = [
            TranscriptUtterance(
                text=segment.text.strip(),
                start_seconds=float(segment.start) if segment.start is not None else None,
                end_seconds=float(segment.end) if segment.end is not None else None,
            )
            for segment in segments
            if segment.text.strip()
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
            language=getattr(info, "language", None),
            duration_seconds=getattr(info, "duration", None),
            utterances=utterances,
        )
