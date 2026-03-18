from __future__ import annotations

import logging
from pathlib import Path
import threading
import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from meeting_summary.processor import CallProcessor

LOGGER = logging.getLogger(__name__)


class CallWatcher(FileSystemEventHandler):
    def __init__(
        self,
        calls_dir: Path,
        processor: CallProcessor,
        ready_checks: int,
        ready_interval_seconds: float,
    ) -> None:
        self.calls_dir = calls_dir
        self.processor = processor
        self.ready_checks = ready_checks
        self.ready_interval_seconds = ready_interval_seconds
        self._active: set[Path] = set()
        self._lock = threading.Lock()

    def process_existing(self) -> None:
        for audio_path in sorted(self.calls_dir.glob("*.m4a")):
            self._schedule(audio_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(Path(event.dest_path))

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

    def _schedule(self, audio_path: Path) -> None:
        if audio_path.suffix.lower() != ".m4a":
            return

        with self._lock:
            if audio_path in self._active:
                return
            self._active.add(audio_path)

        thread = threading.Thread(
            target=self._process_when_ready,
            args=(audio_path,),
            daemon=True,
        )
        thread.start()

    def _process_when_ready(self, audio_path: Path) -> None:
        try:
            if not self._wait_until_stable(audio_path):
                LOGGER.warning("File %s did not stabilize in time, skipping.", audio_path.name)
                return
            self.processor.process(audio_path)
        except Exception:
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

