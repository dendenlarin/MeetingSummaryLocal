from __future__ import annotations

from pathlib import Path

from meeting_summary.config import Settings
from meeting_summary.logging_utils import configure_logging
from meeting_summary.ollama_client import OllamaClient
from meeting_summary.processor import CallProcessor
from meeting_summary.transcriber import Transcriber
from meeting_summary.watcher import CallWatcher


def main() -> None:
    configure_logging()
    settings = Settings.load(base_dir=Path.cwd())
    settings.calls_dir.mkdir(parents=True, exist_ok=True)

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
        enable_diarization=settings.enable_diarization,
        diarization_auth_token=settings.hf_token,
        diarization_device=settings.pyannote_device,
    )
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
    )

    if settings.initial_scan:
        watcher.process_existing()

    watcher.serve_forever()


if __name__ == "__main__":
    main()
