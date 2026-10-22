from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class Rule:
    name: str
    extensions: tuple[str, ...]
    mime_prefixes: tuple[str, ...]
    folder: str


@dataclass(frozen=True)
class Settings:
    watch: Path
    destination: Path
    database: Path
    stable_seconds: float
    poll_interval_seconds: float
    incomplete_suffixes: tuple[str, ...]
    organize_unknown: bool
    rules: tuple[Rule, ...]


def load_settings(path: Path) -> Settings:
    with path.open("rb") as stream:
        data: dict[str, Any] = tomllib.load(stream)

    paths = data.get("paths", {})
    behavior = data.get("behavior", {})
    rules = tuple(
        Rule(
            name=str(item["name"]),
            extensions=tuple(str(x).lower() for x in item.get("extensions", [])),
            mime_prefixes=tuple(str(x).lower() for x in item.get("mime_prefixes", [])),
            folder=str(item["folder"]),
        )
        for item in data.get("rules", [])
    )

    destination = expand_path(paths.get("destination", "~/Downloads/Organized"))
    watch = expand_path(paths.get("watch", "~/Downloads"))
    # Refuse dangerous or nonsensical configurations before starting the watcher.
    if destination == Path.home().resolve() or destination == Path("/"):
        raise ValueError("Destination must not be your home directory or filesystem root.")
    if destination == watch:
        raise ValueError("Destination must differ from the watched directory.")
    for rule in rules:
        folder = Path(rule.folder)
        if folder.is_absolute() or ".." in folder.parts:
            raise ValueError(f"Unsafe destination folder in rule {rule.name!r}: {rule.folder!r}")

    return Settings(
        watch=watch,
        destination=destination,
        database=expand_path(paths.get("database", "~/.local/share/sortwise/history.sqlite3")),
        stable_seconds=max(0.0, float(behavior.get("stable_seconds", 3))),
        poll_interval_seconds=max(0.2, float(behavior.get("poll_interval_seconds", 1))),
        incomplete_suffixes=tuple(
            str(x).lower() for x in behavior.get(
                "incomplete_suffixes",
                [".crdownload", ".part", ".partial", ".download", ".tmp"],
            )
        ),
        organize_unknown=bool(behavior.get("organize_unknown", True)),
        rules=rules,
    )
