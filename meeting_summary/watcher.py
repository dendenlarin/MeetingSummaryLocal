from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import logging
from pathlib import Path
import threading
import time

from meeting_summary.markdown_writer import markdown_path_for
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from meeting_summary.processor import CallProcessor

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class _RecentAttempt:
    fingerprint: tuple[int, int]
    timestamp_monotonic: float
    result: str


class CallWatcher(FileSystemEventHandler):
    def __init__(
        self,
        calls_dir: Path,
        processor: CallProcessor,
        ready_checks: int,
        ready_interval_seconds: float,
        duplicate_cooldown_seconds: float,
    ) -> None:
        self.calls_dir = calls_dir
        self.processor = processor
        self.ready_checks = ready_checks
        self.ready_interval_seconds = ready_interval_seconds
        self.duplicate_cooldown_seconds = duplicate_cooldown_seconds
        self._active: set[Path] = set()
        self._recent_attempts: dict[Path, _RecentAttempt] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="call-watcher",
        )

    def process_existing(self) -> None:
        for audio_path in sorted(self.calls_dir.glob("*.m4a")):
            self._schedule(audio_path, reason="initial_scan")

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.src_path), reason="created")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.dest_path), reason="moved")

    def serve_forever(self) -> None:
        observer = Observer()
        observer.schedule(self, str(self.calls_dir), recursive=False)
        observer.start()
        LOGGER.info("Watching %s for new m4a files.", self.calls_dir)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOGGER.info("Stopping watcher.")
        finally:
            observer.stop()
            observer.join()
            self._executor.shutdown(wait=True)

    def _schedule(self, audio_path: Path, reason: str) -> None:
        if audio_path.suffix.lower() != ".m4a":
            return
        audio_path = audio_path.resolve()

        with self._lock:
            if audio_path in self._active:
                LOGGER.info(
                    "[%s] 0%% | duplicate_suppressed | Ignoring %s event because the file is already active.",
                    audio_path.name,
                    reason,
                )
                return
            self._active.add(audio_path)

        try:
            self._executor.submit(self._process_when_ready, audio_path, reason)
        except Exception:
            with self._lock:
                self._active.discard(audio_path)
            raise

    def _process_when_ready(self, audio_path: Path, reason: str) -> None:
        audio_path = audio_path.resolve()
        try:
            LOGGER.info(
                "[%s] 0%% | waiting_for_file | Waiting for file size to stabilize (reason=%s).",
                audio_path.name,
                reason,
            )
            if not self._wait_until_stable(audio_path):
                LOGGER.warning("File %s did not stabilize in time, skipping.", audio_path.name)
                return
            fingerprint = _fingerprint(audio_path)
            duplicate = self._recent_duplicate(audio_path, fingerprint)
            if duplicate is not None:
                age_seconds, previous_result = duplicate
                if not self._should_allow_retry(audio_path, previous_result):
                    LOGGER.info(
                        "[%s] 0%% | duplicate_suppressed | Suppressed duplicate %s event for unchanged file "
                        "(previous_result=%s, age=%.1fs).",
                        audio_path.name,
                        reason,
                        previous_result,
                        age_seconds,
                    )
                    self._remember_attempt(audio_path, fingerprint, "skipped_duplicate")
                    return

            self._remember_attempt(audio_path, fingerprint, "started")
            result = self.processor.process(audio_path)
            self._remember_attempt(
                audio_path,
                fingerprint,
                "completed" if result is not None else "skipped",
            )
        except Exception:
            if audio_path.exists():
                self._remember_attempt(audio_path, _fingerprint(audio_path), "failed")
            LOGGER.exception("Failed to process %s.", audio_path.name)
        finally:
            with self._lock:
                self._active.discard(audio_path)

    def _wait_until_stable(self, audio_path: Path) -> bool:
        stable_checks = 0
        last_size: int | None = None

        while stable_checks < self.ready_checks:
            if not audio_path.exists():
                return False

            size = audio_path.stat().st_size
            if size > 0 and size == last_size:
                stable_checks += 1
            else:
                stable_checks = 0
                last_size = size

            time.sleep(self.ready_interval_seconds)

        return True

    def _recent_duplicate(
        self,
        audio_path: Path,
        fingerprint: tuple[int, int],
    ) -> tuple[float, str] | None:
        with self._lock:
            recent_attempt = self._recent_attempts.get(audio_path)

        if recent_attempt is None or recent_attempt.fingerprint != fingerprint:
            return None

        age_seconds = time.monotonic() - recent_attempt.timestamp_monotonic
        if age_seconds > self.duplicate_cooldown_seconds:
            return None

        return age_seconds, recent_attempt.result

    def _should_allow_retry(
        self,
        audio_path: Path,
        previous_result: str,
    ) -> bool:
        if previous_result not in {"completed", "skipped"}:
            return False

        return not markdown_path_for(audio_path).exists()

    def _remember_attempt(
        self,
        audio_path: Path,
        fingerprint: tuple[int, int],
        result: str,
    ) -> None:
        with self._lock:
            self._prune_recent_attempts_locked(time.monotonic())
            self._recent_attempts[audio_path] = _RecentAttempt(
                fingerprint=fingerprint,
                timestamp_monotonic=time.monotonic(),
                result=result,
            )

    def _prune_recent_attempts_locked(self, now_monotonic: float) -> None:
        stale_paths = [
            path
            for path, attempt in self._recent_attempts.items()
            if now_monotonic - attempt.timestamp_monotonic > self.duplicate_cooldown_seconds
        ]
        for stale_path in stale_paths:
            self._recent_attempts.pop(stale_path, None)


def _fingerprint(audio_path: Path) -> tuple[int, int]:
    stat_result = audio_path.stat()
    return stat_result.st_size, stat_result.st_mtime_ns
