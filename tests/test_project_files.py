from __future__ import annotations

import os
import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectFilesTests(unittest.TestCase):
    def test_gitignore_excludes_tasks_directory(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("tasks/", gitignore)

    def test_docker_files_are_removed(self) -> None:
        self.assertFalse((PROJECT_ROOT / "Dockerfile").exists())
        self.assertFalse((PROJECT_ROOT / "docker-compose.yml").exists())
        self.assertFalse((PROJECT_ROOT / "constraints-docker.txt").exists())
        self.assertFalse((PROJECT_ROOT / ".dockerignore").exists())

    def test_env_example_uses_native_safe_defaults(self) -> None:
        env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("OLLAMA_PROMPT_PATH=./meeting_summary/prompts/summary.md", env_example)
        self.assertIn("WHISPER_MODEL=medium", env_example)
        self.assertIn("WHISPER_COMPUTE_TYPE=auto", env_example)
        self.assertIn("HF_TOKEN=", env_example)
        self.assertNotIn("ENABLE_DIARIZATION", env_example)

    def test_pyannote_is_required_dependency(self) -> None:
        pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        dependencies = pyproject["project"]["dependencies"]

        self.assertEqual(pyproject["project"]["requires-python"], ">=3.11,<3.14")
        self.assertIn("pyannote.audio==4.0.4", dependencies)
        self.assertNotIn("optional-dependencies", pyproject)

    def test_readme_documents_native_only_flow(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("./run", readme)
        self.assertIn("diarization всегда включён", readme.lower())
        self.assertIn("только нативный macOS runtime", readme)
        self.assertIn("speaker-diarization-community-1", readme)
        self.assertIn("python3.13", readme)
        self.assertNotIn("docker compose", readme.lower())
        self.assertNotIn("ffmpeg", readme.lower())

    def test_run_script_exists_and_is_executable(self) -> None:
        run_script = PROJECT_ROOT / "run"

        self.assertTrue(run_script.exists())
        self.assertTrue(os.access(run_script, os.X_OK))


if __name__ == "__main__":
    unittest.main()
