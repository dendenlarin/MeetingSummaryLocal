from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from meeting_summary.models import TranscriptUtterance

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SpeakerTurn:
    speaker: str
    start_seconds: float
    end_seconds: float


def assign_speakers(
    segments: list[TranscriptUtterance],
    speaker_turns: list[SpeakerTurn],
) -> list[TranscriptUtterance]:
    if not speaker_turns:
        return list(segments)

    assigned_segments: list[TranscriptUtterance] = []
    for segment in segments:
        assigned_segments.append(
            TranscriptUtterance(
                text=segment.text,
                speaker=_select_speaker(segment, speaker_turns),
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
            )
        )
    return _normalize_speaker_labels(assigned_segments)


def _select_speaker(
    segment: TranscriptUtterance,
    speaker_turns: list[SpeakerTurn],
) -> str | None:
    if segment.start_seconds is None or segment.end_seconds is None:
        return None

    best_speaker: str | None = None
    best_overlap = 0.0
    for turn in speaker_turns:
        overlap = _overlap_seconds(
            segment.start_seconds,
            segment.end_seconds,
            turn.start_seconds,
            turn.end_seconds,
        )
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = turn.speaker

    return best_speaker


def _overlap_seconds(
    left_start: float,
    left_end: float,
    right_start: float,
    right_end: float,
) -> float:
    start = max(left_start, right_start)
    end = min(left_end, right_end)
    return max(0.0, end - start)


def _normalize_speaker_labels(
    utterances: list[TranscriptUtterance],
) -> list[TranscriptUtterance]:
    speaker_map: dict[str, str] = {}
    normalized: list[TranscriptUtterance] = []

    for utterance in utterances:
        speaker = utterance.speaker
        if speaker is not None and speaker not in speaker_map:
            speaker_map[speaker] = f"Speaker {len(speaker_map) + 1}"

        normalized.append(
            TranscriptUtterance(
                text=utterance.text,
                speaker=speaker_map.get(speaker) if speaker is not None else None,
                start_seconds=utterance.start_seconds,
                end_seconds=utterance.end_seconds,
            )
        )

    return normalized


class PyannoteDiarizer:
    def __init__(
        self,
        auth_token: str | None = None,
        device: str = "auto",
        model_name: str = "pyannote/speaker-diarization-3.1",
    ) -> None:
        from pyannote.audio import Pipeline

        self.pipeline = Pipeline.from_pretrained(
            model_name,
            use_auth_token=auth_token or None,
        )
        self._move_pipeline_to_device(device)
        LOGGER.info("Loaded pyannote diarization pipeline '%s'.", model_name)

    def diarize(self, audio_path: Path) -> list[SpeakerTurn]:
        annotation = self.pipeline(str(audio_path))
        speaker_turns: list[SpeakerTurn] = []
        for segment, _, speaker in annotation.itertracks(yield_label=True):
            speaker_turns.append(
                SpeakerTurn(
                    speaker=str(speaker),
                    start_seconds=float(segment.start),
                    end_seconds=float(segment.end),
                )
            )
        return speaker_turns

    def _move_pipeline_to_device(self, device: str) -> None:
        import torch

        if device == "auto":
            target_device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            target_device = device

        self.pipeline.to(torch.device(target_device))
        LOGGER.info("Using pyannote device=%s.", target_device)
