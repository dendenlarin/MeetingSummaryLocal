from __future__ import annotations

import logging
from pathlib import Path

from meeting_summary.models import TranscriptionResult

LOGGER = logging.getLogger(__name__)


class Transcriber:
    def __init__(
        self,
        model_size: str,
        device: str,
        compute_type: str,
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

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        segments, info = self.model.transcribe(str(audio_path), vad_filter=True)
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())

        if not transcript:
            raise RuntimeError(f"Transcription for {audio_path.name} is empty.")

        return TranscriptionResult(
            source_path=audio_path,
            transcript=transcript,
            language=getattr(info, "language", None),
            duration_seconds=getattr(info, "duration", None),
        )

