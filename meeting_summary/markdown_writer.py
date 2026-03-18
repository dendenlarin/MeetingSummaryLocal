from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from meeting_summary.models import CallSummary, TranscriptionResult


def build_markdown(
    transcription: TranscriptionResult,
    summary: CallSummary,
) -> str:
    processed_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    language = transcription.language or "unknown"
    duration = (
        f"{transcription.duration_seconds:.1f} sec"
        if transcription.duration_seconds is not None
        else "unknown"
    )

    return "\n".join(
        [
            f"# {transcription.source_path.name}",
            "",
            f"- Processed at: {processed_at}",
            f"- Language: {language}",
            f"- Duration: {duration}",
            "",
            "## Summary",
            "",
            summary.content.strip(),
            "",
            "## Transcript",
            "",
            transcription.transcript.strip(),
            "",
        ]
    )


def markdown_path_for(audio_path: Path) -> Path:
    return audio_path.with_suffix(".md")

