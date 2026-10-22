from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import load_settings
from .history import History
from .organizer import Organizer
from .watcher import run_watcher


def _default_config() -> Path:
    candidates = [
        Path.cwd() / "config.toml",
        Path.home() / ".config" / "sortwise" / "config.toml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(prog="sortwise", description="Safely organize your Downloads folder.")
    parser.add_argument("--config", type=Path, default=_default_config(), help="Path to config.toml")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("watch", help="Watch Downloads and automatically organize completed items")
    sub.add_parser("organize-existing", help="Organize current top-level items in Downloads")
    undo_parser = sub.add_parser("undo", help="Undo the most recent move or a specific move ID")
    undo_parser.add_argument("--id", type=int, help="Move ID to undo")
    history_parser = sub.add_parser("history", help="Show recent moves")
    history_parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings(args.config)
    history = History(settings.database)
    organizer = Organizer(settings, history)

    if args.command == "watch":
        run_watcher(organizer)
    elif args.command == "organize-existing":
        for item in settings.watch.iterdir():
            if item.resolve() == settings.destination.resolve() or organizer._is_inside_destination(item):
                continue
            organizer.organize(item)
    elif args.command == "undo":
        raise SystemExit(0 if organizer.undo(args.id) else 1)
    elif args.command == "history":
        for row in history.list_recent(max(1, args.limit)):
            print(f"#{row['id']} [{row['status']}] {row['original_path']} -> {row['moved_path']} ({row['moved_at']})")


if __name__ == "__main__":
    main()
