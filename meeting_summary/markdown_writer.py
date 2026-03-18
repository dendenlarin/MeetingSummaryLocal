from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from meeting_summary.models import CallSummary, TranscriptUtterance, TranscriptionResult


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
    speakers_detected = "yes" if _has_speaker_labels(transcription) else "no"
    transcript_body = _build_transcript_body(transcription)

    return "\n".join(
        [
            f"# {transcription.source_path.name}",
            "",
            f"- Processed at: {processed_at}",
            f"- Language: {language}",
            f"- Duration: {duration}",
            f"- Speakers detected: {speakers_detected}",
            "",
            "## Summary",
            "",
            summary.content.strip(),
            "",
            "## Transcript",
            "",
            transcript_body,
            "",
        ]
    )


def markdown_path_for(audio_path: Path) -> Path:
    return audio_path.with_suffix(".md")


def _build_transcript_body(transcription: TranscriptionResult) -> str:
    if not _has_speaker_labels(transcription):
        return transcription.transcript.strip()

    return "\n".join(_format_utterance(utterance) for utterance in transcription.utterances)


def _format_utterance(utterance: TranscriptUtterance) -> str:
    speaker = utterance.speaker or "Speaker ?"
    if utterance.start_seconds is None or utterance.end_seconds is None:
        return f"{speaker}: {utterance.text}"

    return (
        f"[{_format_timestamp(utterance.start_seconds)}-{_format_timestamp(utterance.end_seconds)}] "
        f"{speaker}: {utterance.text}"
    )


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, seconds_part = divmod(total_seconds, 60)
    hours, minutes_part = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes_part:02d}:{seconds_part:02d}"
    return f"{minutes_part:02d}:{seconds_part:02d}"


def _has_speaker_labels(transcription: TranscriptionResult) -> bool:
    return any(utterance.speaker for utterance in transcription.utterances)
