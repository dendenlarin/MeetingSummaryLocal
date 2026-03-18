from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TranscriptionResult:
    source_path: Path
    transcript: str
    language: str | None
    duration_seconds: float | None


@dataclass(slots=True)
class CallSummary:
    content: str

