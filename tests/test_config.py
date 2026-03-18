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

    def test_empty_enable_diarization_is_treated_as_disabled(self) -> None:
        with patch.dict(os.environ, {"ENABLE_DIARIZATION": ""}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertFalse(settings.enable_diarization)

    def test_true_enable_diarization_is_treated_as_enabled(self) -> None:
        with patch.dict(os.environ, {"ENABLE_DIARIZATION": "true"}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertTrue(settings.enable_diarization)

    def test_empty_initial_scan_is_treated_as_disabled(self) -> None:
        with patch.dict(os.environ, {"INITIAL_SCAN": ""}, clear=True):
            settings = Settings.load(base_dir=self.base_dir)

        self.assertFalse(settings.initial_scan)


if __name__ == "__main__":
    unittest.main()
