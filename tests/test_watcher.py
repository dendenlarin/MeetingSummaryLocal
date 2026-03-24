from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from meeting_summary.watcher import CallWatcher


class CallWatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.calls_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_process_existing_schedules_initial_scan_reason(self) -> None:
        audio_path = self.calls_dir / "existing.m4a"
        audio_path.write_bytes(b"audio")
        processor = Mock()
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        with patch.object(watcher, "_schedule") as schedule_mock:
            watcher.process_existing()

        schedule_mock.assert_called_once_with(audio_path, reason="initial_scan")

    def test_created_and_moved_events_pass_event_reason(self) -> None:
        processor = Mock()
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        with patch.object(watcher, "_schedule") as schedule_mock:
            watcher.on_created(SimpleNamespace(is_directory=False, src_path="/tmp/demo.m4a"))
            watcher.on_moved(
                SimpleNamespace(is_directory=False, dest_path="/tmp/renamed-demo.m4a")
            )

        self.assertEqual(
            schedule_mock.call_args_list,
            [
                call(Path("/tmp/demo.m4a"), reason="created"),
                call(Path("/tmp/renamed-demo.m4a"), reason="moved"),
            ],
        )

    def test_process_when_ready_suppresses_recent_duplicate_fingerprint(self) -> None:
        audio_path = self.calls_dir / "demo.m4a"
        audio_path.write_bytes(b"audio")
        processor = Mock()
        markdown_path = audio_path.with_suffix(".md")

        def _complete_processing(_: Path) -> Path:
            markdown_path.write_text("done\n", encoding="utf-8")
            return markdown_path

        processor.process.side_effect = _complete_processing
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        watcher._process_when_ready(audio_path, reason="created")
        with patch("meeting_summary.watcher.LOGGER") as logger_mock:
            watcher._process_when_ready(audio_path, reason="moved")

        processor.process.assert_called_once_with(audio_path.resolve())
        duplicate_logs = [
            log_call
            for log_call in logger_mock.info.call_args_list
            if log_call.args and "duplicate_suppressed" in log_call.args[0]
        ]
        self.assertTrue(duplicate_logs)

    def test_process_when_ready_allows_retry_when_markdown_was_removed(self) -> None:
        audio_path = self.calls_dir / "demo.m4a"
        audio_path.write_bytes(b"audio")
        markdown_path = audio_path.with_suffix(".md")
        processor = Mock()

        def _complete_processing(_: Path) -> Path:
            markdown_path.write_text("done\n", encoding="utf-8")
            return markdown_path

        processor.process.side_effect = _complete_processing
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        watcher._process_when_ready(audio_path, reason="created")
        markdown_path.unlink()
        watcher._process_when_ready(audio_path, reason="moved")

        self.assertEqual(processor.process.call_count, 2)

    def test_process_when_ready_allows_changed_fingerprint_inside_cooldown(self) -> None:
        audio_path = self.calls_dir / "demo.m4a"
        audio_path.write_bytes(b"audio")
        processor = Mock()
        processor.process.return_value = audio_path.with_suffix(".md")
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        watcher._process_when_ready(audio_path, reason="created")
        audio_path.write_bytes(b"audio-updated-with-new-fingerprint")
        watcher._process_when_ready(audio_path, reason="moved")

        self.assertEqual(processor.process.call_count, 2)

    def test_remember_attempt_prunes_stale_entries(self) -> None:
        audio_path = self.calls_dir / "demo.m4a"
        audio_path.write_bytes(b"audio")
        processor = Mock()
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        stale_path = (self.calls_dir / "stale.m4a").resolve()
        watcher._recent_attempts[stale_path] = unittest.mock.Mock(
            fingerprint=(1, 1),
            timestamp_monotonic=0.0,
            result="completed",
        )

        with patch("meeting_summary.watcher.time.monotonic", return_value=200.0):
            watcher._remember_attempt(audio_path.resolve(), (5, 5), "started")

        self.assertNotIn(stale_path, watcher._recent_attempts)
        self.assertIn(audio_path.resolve(), watcher._recent_attempts)

    def test_process_when_ready_allows_retry_after_cooldown(self) -> None:
        audio_path = self.calls_dir / "demo.m4a"
        audio_path.write_bytes(b"audio")
        processor = Mock()
        processor.process.return_value = audio_path.with_suffix(".md")
        watcher = CallWatcher(
            calls_dir=self.calls_dir,
            processor=processor,
            ready_checks=0,
            ready_interval_seconds=0,
            duplicate_cooldown_seconds=120,
        )

        watcher._process_when_ready(audio_path, reason="created")
        resolved_path = audio_path.resolve()
        watcher._recent_attempts[resolved_path].timestamp_monotonic -= 121
        watcher._process_when_ready(audio_path, reason="moved")

        self.assertEqual(processor.process.call_count, 2)
