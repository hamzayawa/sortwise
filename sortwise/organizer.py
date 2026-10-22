from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path

from .classifier import classify
from .config import Settings
from .history import History

log = logging.getLogger("sortwise")


class Organizer:
    def __init__(self, settings: Settings, history: History):
        self.settings = settings
        self.history = history
        self.settings.watch.mkdir(parents=True, exist_ok=True)
        self.settings.destination.mkdir(parents=True, exist_ok=True)

    def is_incomplete(self, path: Path) -> bool:
        name = path.name.lower()
        return any(name.endswith(suffix) for suffix in self.settings.incomplete_suffixes)

    def _is_inside_destination(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.settings.destination.resolve())
            return True
        except ValueError:
            return False

    def _is_stable(self, path: Path) -> bool:
        """Wait for an unchanged size and mtime for the configured interval."""
        deadline = time.monotonic() + max(self.settings.stable_seconds + 15, 15)
        last_signature = None
        stable_since = None
        while time.monotonic() < deadline:
            if not path.exists() or self.is_incomplete(path):
                return False
            try:
                stat = path.stat()
                signature = (stat.st_size, stat.st_mtime_ns)
            except OSError:
                return False
            if signature == last_signature:
                if stable_since is None:
                    stable_since = time.monotonic()
                if time.monotonic() - stable_since >= self.settings.stable_seconds:
                    return True
            else:
                last_signature = signature
                stable_since = time.monotonic()
            time.sleep(self.settings.poll_interval_seconds)
        log.warning("Timed out waiting for download to stabilize: %s", path)
        return False

    @staticmethod
    def _unique_path(path: Path) -> Path:
        """Choose a non-existing destination without overwriting anything."""
        if not path.exists():
            return path
        for index in range(1, 100_000):
            candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
            if not candidate.exists():
                return candidate
        raise RuntimeError(f"Could not find a free filename for {path}")

    def organize(self, path: Path, wait_for_stability: bool = True) -> Path | None:
        path = path.expanduser().absolute()
        if self._is_inside_destination(path) or path.name.startswith(".sortwise-"):
            return None
        if not path.exists() or self.is_incomplete(path):
            return None
        if path.resolve() == self.settings.watch.resolve():
            return None
        if wait_for_stability and not self._is_stable(path):
            return None

        folder = classify(path, self.settings)
        if folder is None:
            log.info("Leaving unknown item in place: %s", path)
            return None

        target_dir = (self.settings.destination / folder).resolve()
        try:
            target_dir.relative_to(self.settings.destination.resolve())
        except ValueError:
            raise ValueError(f"Unsafe destination folder: {folder}")
        target_dir.mkdir(parents=True, exist_ok=True)
        target = self._unique_path(target_dir / path.name)

        try:
            # os.replace is deliberately not used: it can overwrite existing files.
            # Same-filesystem rename is atomic; shutil.move handles cross-filesystem moves.
            shutil.move(str(path), str(target))
            self.history.record_move(path, target)
            log.info("Moved %s -> %s", path, target)
            return target
        except (OSError, shutil.Error):
            log.exception("Could not move %s", path)
            return None

    def undo(self, move_id: int | None = None) -> bool:
        row = self.history.latest(move_id)
        if row is None:
            log.warning("No matching move available to undo.")
            return False
        moved = Path(row["moved_path"])
        original = Path(row["original_path"])
        if not moved.exists():
            log.error("Cannot undo: moved item no longer exists: %s", moved)
            return False
        if original.exists():
            log.error("Cannot undo without overwriting: original path already exists: %s", original)
            return False
        original.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(moved), str(original))
            self.history.mark_undone(int(row["id"]))
            log.info("Undid move #%s: %s -> %s", row["id"], moved, original)
            return True
        except (OSError, shutil.Error):
            log.exception("Undo failed for move #%s", row["id"])
            return False
