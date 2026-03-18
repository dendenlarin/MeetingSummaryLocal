from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    calls_dir: Path
    ollama_model: str
    ollama_base_url: str
    ollama_prompt_path: Path
    whisper_model_size: str
    whisper_device: str
    whisper_compute_type: str
    enable_diarization: bool
    hf_token: str | None
    pyannote_device: str
    file_ready_checks: int
    file_ready_interval_seconds: float
    initial_scan: bool

    @classmethod
    def load(cls, base_dir: Path | None = None) -> "Settings":
        root = base_dir or Path.cwd()
        load_dotenv(root / ".env")

        return cls(
            calls_dir=(root / os.getenv("CALLS_DIR", "calls")).resolve(),
            ollama_model=os.getenv("OLLAMA_MODEL", "auto"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_prompt_path=Path(
                os.getenv(
                    "OLLAMA_PROMPT_PATH",
                    str(root / "meeting_summary" / "prompts" / "summary.md"),
                )
            ).resolve(),
            whisper_model_size=os.getenv("WHISPER_MODEL_SIZE", "small"),
            whisper_device=os.getenv("WHISPER_DEVICE", "auto"),
            whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "default"),
            enable_diarization=(
                os.getenv("ENABLE_DIARIZATION", "false").lower() not in {"0", "false", "no"}
            ),
            hf_token=os.getenv("HF_TOKEN") or None,
            pyannote_device=os.getenv("PYANNOTE_DEVICE", "auto"),
            file_ready_checks=int(os.getenv("FILE_READY_CHECKS", "3")),
            file_ready_interval_seconds=float(
                os.getenv("FILE_READY_INTERVAL_SECONDS", "2")
            ),
            initial_scan=os.getenv("INITIAL_SCAN", "true").lower() not in {"0", "false", "no"},
        )
