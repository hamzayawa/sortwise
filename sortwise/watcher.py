from __future__ import annotations

import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .organizer import Organizer

log = logging.getLogger("sortwise")


class DownloadHandler(FileSystemEventHandler):
    def __init__(self, organizer: Organizer):
        self.organizer = organizer
        self._scheduled: set[str] = set()
        self._lock = threading.Lock()

    def _schedule(self, raw_path: str) -> None:
        path = Path(raw_path)
        if self.organizer._is_inside_destination(path) or self.organizer.is_incomplete(path):
            return
        key = str(path.absolute())
        with self._lock:
            if key in self._scheduled:
                return
            self._scheduled.add(key)

        def worker():
            try:
                self.organizer.organize(path, wait_for_stability=True)
            finally:
                with self._lock:
                    self._scheduled.discard(key)

        threading.Thread(target=worker, name="sortwise-move", daemon=True).start()

    def on_created(self, event: FileSystemEvent) -> None:
        self._schedule(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        # Browsers commonly rename a temporary download to its final name on completion.
        self._schedule(event.dest_path)


def run_watcher(organizer: Organizer) -> None:
    handler = DownloadHandler(organizer)
    observer = Observer()
    observer.schedule(handler, str(organizer.settings.watch), recursive=False)
    observer.start()
    log.info("Watching %s; destination: %s", organizer.settings.watch, organizer.settings.destination)
    try:
        observer.join()
    except KeyboardInterrupt:
        log.info("Stopping SortWise...")
    finally:
        observer.stop()
        observer.join()
