from __future__ import annotations

import os
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from meeting_summary.config import Settings


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_uses_packaged_prompt_by_default(self) -> None:
        expected_prompt_path = Path(
            str(files("meeting_summary.prompts").joinpath("summary.md"))
        ).resolve()

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.ollama_prompt_path, expected_prompt_path)
        self.assertTrue(settings.ollama_prompt_path.is_file())

    def test_load_uses_explicit_prompt_override(self) -> None:
        custom_prompt_path = self.base_dir / "custom-summary.md"
        custom_prompt_path.write_text("CUSTOM\n", encoding="utf-8")

        with patch.dict(
            os.environ,
            {"OLLAMA_PROMPT_PATH": str(custom_prompt_path)},
            clear=True,
        ):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.ollama_prompt_path, custom_prompt_path.resolve())

    def test_load_resolves_relative_prompt_override_from_base_dir(self) -> None:
        prompts_dir = self.base_dir / "prompts"
        prompts_dir.mkdir()
        custom_prompt_path = prompts_dir / "summary.md"
        custom_prompt_path.write_text("CUSTOM\n", encoding="utf-8")

        with patch.dict(
            os.environ,
            {"OLLAMA_PROMPT_PATH": "./prompts/summary.md"},
            clear=True,
        ):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.ollama_prompt_path, custom_prompt_path.resolve())

    def test_load_applies_balanced_native_whisper_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.whisper_model, "medium")
        self.assertEqual(settings.whisper_compute_type, "auto")
        self.assertIsNone(settings.whisper_language)
        self.assertIsNone(settings.whisper_initial_prompt)
        self.assertEqual(settings.whisper_terms, ())
        self.assertEqual(settings.whisper_beam_size, 5)
        self.assertEqual(settings.whisper_best_of, 5)
        self.assertEqual(settings.whisper_temperature, 0.0)
        self.assertTrue(settings.whisper_vad_filter)

    def test_load_reads_explicit_whisper_quality_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "WHISPER_LANGUAGE": "ru",
                "WHISPER_INITIAL_PROMPT": "Docker GitHub API",
                "WHISPER_TERMS": "Docker, GitHub, API, deploy",
                "WHISPER_COMPUTE_TYPE": "float16",
                "WHISPER_BEAM_SIZE": "7",
                "WHISPER_BEST_OF": "6",
                "WHISPER_TEMPERATURE": "0.2",
                "WHISPER_VAD_FILTER": "false",
            },
            clear=True,
        ):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.whisper_language, "ru")
        self.assertEqual(settings.whisper_initial_prompt, "Docker GitHub API")
        self.assertEqual(settings.whisper_terms, ("Docker", "GitHub", "API", "deploy"))
        self.assertEqual(settings.whisper_compute_type, "float16")
        self.assertEqual(settings.whisper_beam_size, 7)
        self.assertEqual(settings.whisper_best_of, 6)
        self.assertEqual(settings.whisper_temperature, 0.2)
        self.assertFalse(settings.whisper_vad_filter)

    def test_empty_initial_scan_is_treated_as_disabled(self) -> None:
        with patch.dict(os.environ, {"INITIAL_SCAN": ""}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertFalse(settings.initial_scan)

    def test_load_reads_duplicate_cooldown_seconds(self) -> None:
        with patch.dict(
            os.environ,
            {"FILE_DUPLICATE_COOLDOWN_SECONDS": "45"},
            clear=True,
        ):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.file_duplicate_cooldown_seconds, 45.0)

    def test_load_uses_duplicate_cooldown_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertEqual(settings.file_duplicate_cooldown_seconds, 120.0)


if __name__ == "__main__":
    unittest.main()
