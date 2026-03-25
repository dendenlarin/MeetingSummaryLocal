from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProjectFilesTests(unittest.TestCase):
    def test_gitignore_excludes_tasks_directory(self) -> None:
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("tasks/", gitignore)

    def test_docker_compose_mounts_prompt_directory(self) -> None:
        docker_compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("./meeting_summary/prompts:/app/runtime-prompts:ro", docker_compose)
        self.assertNotIn(
            "./meeting_summary/prompts/summary.md:/app/runtime-prompts/summary.md:ro",
            docker_compose,
        )

    def test_docker_compose_exposes_duplicate_cooldown_env(self) -> None:
        docker_compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn(
            'FILE_DUPLICATE_COOLDOWN_SECONDS: "${FILE_DUPLICATE_COOLDOWN_SECONDS:-120}"',
            docker_compose,
        )

    def test_pyannote_is_optional_dependency(self) -> None:
        pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        dependencies = pyproject["project"]["dependencies"]
        optional_dependencies = pyproject["project"]["optional-dependencies"]["diarization"]

        self.assertFalse(any(dep.startswith("pyannote.audio") for dep in dependencies))
        self.assertTrue(any(dep.startswith("pyannote.audio") for dep in optional_dependencies))

    def test_dockerfile_installs_diarization_extra(self) -> None:
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn('pip install --constraint constraints-docker.txt ".[diarization]"', dockerfile)


if __name__ == "__main__":
    unittest.main()
