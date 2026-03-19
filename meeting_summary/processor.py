from __future__ import annotations

import logging
from pathlib import Path
import tempfile

from meeting_summary.markdown_writer import build_markdown, markdown_path_for
from meeting_summary.models import CallSummary, TranscriptionResult
from meeting_summary.ollama_client import OllamaClient
from meeting_summary.transcriber import Transcriber

LOGGER = logging.getLogger(__name__)


class CallProcessor:
    def __init__(
        self,
        transcriber: Transcriber,
        ollama_client: OllamaClient,
    ) -> None:
        self.transcriber = transcriber
        self.ollama_client = ollama_client

    def should_process(self, audio_path: Path) -> bool:
        return audio_path.suffix.lower() == ".m4a" and not markdown_path_for(audio_path).exists()

    def process(self, audio_path: Path) -> Path | None:
        if not self.should_process(audio_path):
            LOGGER.info(
                "Skipping %s because markdown output already exists or extension is unsupported.",
                audio_path.name,
            )
            return None

        progress = _progress_logger(audio_path)
        progress("processing_started", 10, "File is stable. Starting analysis.")

        current_stage = "transcribing"
        try:
            transcription = self.transcriber.transcribe(
                audio_path,
                progress_callback=progress,
            )
            current_stage = "summarizing"
            progress("summarizing", 85, "Generating summary with Ollama.")
            summary = self.ollama_client.summarize(transcription)
            current_stage = "writing_output"
            progress("writing_output", 95, "Writing markdown output.")
            target_path = markdown_path_for(audio_path)
            self._write_markdown(target_path, transcription, summary)
            LOGGER.info("Saved summary markdown to %s.", target_path)
            progress("completed", 100, f"Saved markdown to {target_path.name}.")
            return target_path
        except Exception as exc:
            progress("failed", 100, f"Failed during {current_stage}: {exc}")
            raise

    def _write_markdown(
        self,
        target_path: Path,
        transcription: TranscriptionResult,
        summary: CallSummary,
    ) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = build_markdown(transcription=transcription, summary=summary)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target_path.parent,
            delete=False,
            prefix=f".{target_path.stem}.",
            suffix=".tmp",
        ) as handle:
            handle.write(markdown)
            temp_path = Path(handle.name)

        temp_path.replace(target_path)


def _progress_logger(audio_path: Path):
    def _log(stage: str, percent: int, message: str) -> None:
        LOGGER.info("[%s] %s%% | %s | %s", audio_path.name, percent, stage, message)

    return _log
