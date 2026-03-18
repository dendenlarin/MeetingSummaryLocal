from __future__ import annotations

import logging
from typing import Any

import requests

from meeting_summary.models import CallSummary, TranscriptionResult

LOGGER = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Raised when Ollama fails to produce a summary."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model.strip() or "auto"
        self.timeout_seconds = timeout_seconds

    def summarize(self, transcription: TranscriptionResult) -> CallSummary:
        prompt = self._build_prompt(transcription)
        requested_model = self._initial_model()
        response = self._generate(requested_model, prompt)

        if response.status_code >= 400:
            fallback_model = self._fallback_model_for(response, requested_model)
            if fallback_model is not None and fallback_model != requested_model:
                LOGGER.warning(
                    "Ollama model '%s' is unavailable, falling back to installed model '%s'.",
                    requested_model,
                    fallback_model,
                )
                self.model = fallback_model
                response = self._generate(fallback_model, prompt)

        if response.status_code >= 400:
            raise self._build_error(response, requested_model)

        payload = response.json()
        content = (payload.get("response") or "").strip()
        if not content:
            raise OllamaError("Ollama returned an empty summary response.")

        LOGGER.info("Summary generated with Ollama model '%s'.", self.model)
        return CallSummary(content=content)

    def _generate(self, model: str, prompt: str) -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=self.timeout_seconds,
        )

    def _initial_model(self) -> str:
        if self.model.lower() != "auto":
            return self.model

        installed_models = self.list_models()
        if not installed_models:
            raise OllamaError(
                "No local Ollama models were found. Run `ollama pull <model>` and restart the service."
            )

        selected_model = installed_models[0]
        self.model = selected_model
        LOGGER.info("Using auto-selected Ollama model '%s'.", selected_model)
        return selected_model

    def list_models(self) -> list[str]:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=min(self.timeout_seconds, 30),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Failed to query installed Ollama models from {self.base_url}: {exc}"
            ) from exc

        payload: dict[str, Any] = response.json()
        models = payload.get("models", [])
        names = [item.get("name", "").strip() for item in models if item.get("name")]
        return names

    def _fallback_model_for(self, response: requests.Response, requested_model: str) -> str | None:
        if not self._is_model_not_found(response):
            return None

        installed_models = self.list_models()
        if not installed_models:
            return None

        for candidate in installed_models:
            if candidate != requested_model:
                return candidate

        return None

    def _build_error(self, response: requests.Response, requested_model: str) -> OllamaError:
        if self._is_model_not_found(response):
            installed_models = self.list_models()
            available = ", ".join(installed_models) if installed_models else "none"
            return OllamaError(
                f"Ollama model '{requested_model}' was not found. Available local models: {available}. "
                f"Update OLLAMA_MODEL in .env or run `ollama pull {requested_model}`."
            )

        return OllamaError(
            f"Ollama returned HTTP {response.status_code}: {response.text.strip()}"
        )

    @staticmethod
    def _is_model_not_found(response: requests.Response) -> bool:
        if response.status_code != 404:
            return False

        try:
            payload = response.json()
        except ValueError:
            return "not found" in response.text.lower()

        error_message = str(payload.get("error", ""))
        return "not found" in error_message.lower()

    def _build_prompt(self, transcription: TranscriptionResult) -> str:
        return (
            "You summarize phone calls into concise markdown.\n"
            "Return only markdown content, no code fences.\n"
            "Write in Russian.\n"
            "Use these sections when relevant:\n"
            "## Кратко\n"
            "## Договоренности\n"
            "## Следующие шаги\n"
            "## Риски и открытые вопросы\n\n"
            f"Detected language: {transcription.language or 'unknown'}\n"
            f"Duration seconds: {transcription.duration_seconds or 'unknown'}\n\n"
            "Transcript:\n"
            f"{transcription.transcript}\n"
        )
