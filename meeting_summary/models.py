from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class TranscriptUtterance:
    text: str
    speaker: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass(slots=True)
class TranscriptionResult:
    source_path: Path
    transcript: str
    language: str | None
    duration_seconds: float | None
    utterances: list[TranscriptUtterance] = field(default_factory=list)


@dataclass(slots=True)
class CallSummary:
    content: str
