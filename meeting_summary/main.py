from __future__ import annotations

import logging
from pathlib import Path
import sys

from meeting_summary.config import Settings
from meeting_summary.logging_utils import configure_logging
from meeting_summary.ollama_client import OllamaClient
from meeting_summary.processor import CallProcessor
from meeting_summary.transcriber import DiarizationConfigurationError, Transcriber
from meeting_summary.watcher import CallWatcher

LOGGER = logging.getLogger(__name__)


def _ensure_supported_python() -> None:
    if sys.version_info < (3, 11) or sys.version_info >= (3, 14):
        version = f"{sys.version_info[0]}.{sys.version_info[1]}"
        LOGGER.error(
            "Unsupported Python %s. Use Python 3.11, 3.12, or 3.13 for this project.",
            version,
        )
        raise SystemExit(1)


def main() -> None:
    configure_logging()
    _ensure_supported_python()
    settings = Settings.load(base_dir=Path.cwd())
    settings.calls_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Using Ollama prompt template from %s.", settings.ollama_prompt_path)

    if settings.whisper_vad_filter:
        LOGGER.info(
            "WHISPER_VAD_FILTER is enabled. The first transcription progress heartbeat may appear "
            "only after faster-whisper yields segments, so a file can stay at 20%% for a while "
            "without being stuck or restarted."
        )

    try:
        transcriber = Transcriber(
            model_name=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            language=settings.whisper_language,
            initial_prompt=settings.whisper_initial_prompt,
            terms=settings.whisper_terms,
            beam_size=settings.whisper_beam_size,
            best_of=settings.whisper_best_of,
            temperature=settings.whisper_temperature,
            vad_filter=settings.whisper_vad_filter,
            diarization_auth_token=settings.hf_token,
            diarization_device=settings.pyannote_device,
        )
    except DiarizationConfigurationError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc
    ollama_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        prompt_path=settings.ollama_prompt_path,
    )
    processor = CallProcessor(
        transcriber=transcriber,
        ollama_client=ollama_client,
    )
    watcher = CallWatcher(
        calls_dir=settings.calls_dir,
        processor=processor,
        ready_checks=settings.file_ready_checks,
        ready_interval_seconds=settings.file_ready_interval_seconds,
        duplicate_cooldown_seconds=settings.file_duplicate_cooldown_seconds,
    )

    if settings.initial_scan:
        watcher.process_existing()

    watcher.serve_forever()


if __name__ == "__main__":
    main()
