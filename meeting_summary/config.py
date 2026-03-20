from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
import os
import re

from dotenv import load_dotenv


_FALSE_ENV_VALUES = {"", "0", "false", "no"}


def _default_ollama_prompt_path() -> Path:
    return Path(str(files("meeting_summary.prompts").joinpath("summary.md"))).resolve()


def _resolve_ollama_prompt_path(root: Path) -> Path:
    raw_path = os.getenv("OLLAMA_PROMPT_PATH")
    if raw_path is None or not raw_path.strip():
        return _default_ollama_prompt_path()

    prompt_path = Path(raw_path)
    if not prompt_path.is_absolute():
        prompt_path = root / prompt_path

    return prompt_path.resolve()


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() not in _FALSE_ENV_VALUES


def _env_terms(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return ()

    normalized = raw_value.replace("\n", ",").replace(";", ",")
    if "," in normalized:
        parts = normalized.split(",")
    else:
        parts = re.split(r"\s+", normalized)

    terms: list[str] = []
    seen: set[str] = set()
    for part in parts:
        term = part.strip()
        if not term or term in seen:
            continue
        seen.add(term)
        terms.append(term)

    return tuple(terms)


@dataclass(slots=True)
class Settings:
    calls_dir: Path
    ollama_model: str
    ollama_base_url: str
    ollama_prompt_path: Path
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    whisper_language: str | None
    whisper_initial_prompt: str | None
    whisper_terms: tuple[str, ...]
    whisper_beam_size: int
    whisper_best_of: int
    whisper_temperature: float
    whisper_vad_filter: bool
    enable_diarization: bool
    hf_token: str | None
    pyannote_device: str
    file_ready_checks: int
    file_ready_interval_seconds: float
    file_duplicate_cooldown_seconds: float
    initial_scan: bool

    @classmethod
    def load(cls, base_dir: Path | None = None) -> "Settings":
        root = base_dir or Path.cwd()
        load_dotenv(root / ".env")

        return cls(
            calls_dir=(root / os.getenv("CALLS_DIR", "calls")).resolve(),
            ollama_model=os.getenv("OLLAMA_MODEL", "auto"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_prompt_path=_resolve_ollama_prompt_path(root),
            whisper_model=os.getenv("WHISPER_MODEL")
            or os.getenv("WHISPER_MODEL_SIZE")
            or "large-v3",
            whisper_device=os.getenv("WHISPER_DEVICE", "auto"),
            whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "auto"),
            whisper_language=os.getenv("WHISPER_LANGUAGE") or None,
            whisper_initial_prompt=os.getenv("WHISPER_INITIAL_PROMPT") or None,
            whisper_terms=_env_terms("WHISPER_TERMS"),
            whisper_beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
            whisper_best_of=int(os.getenv("WHISPER_BEST_OF", "5")),
            whisper_temperature=float(os.getenv("WHISPER_TEMPERATURE", "0")),
            whisper_vad_filter=_env_flag("WHISPER_VAD_FILTER", default=True),
            enable_diarization=_env_flag("ENABLE_DIARIZATION", default=False),
            hf_token=os.getenv("HF_TOKEN") or None,
            pyannote_device=os.getenv("PYANNOTE_DEVICE", "auto"),
            file_ready_checks=int(os.getenv("FILE_READY_CHECKS", "3")),
            file_ready_interval_seconds=float(
                os.getenv("FILE_READY_INTERVAL_SECONDS", "2")
            ),
            file_duplicate_cooldown_seconds=float(
                os.getenv("FILE_DUPLICATE_COOLDOWN_SECONDS", "120")
            ),
            initial_scan=_env_flag("INITIAL_SCAN", default=True),
        )
