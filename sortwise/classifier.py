from __future__ import annotations

import mimetypes
import zipfile
from pathlib import Path

from .config import Rule, Settings


PROJECT_MARKERS = {
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    "composer.json", "requirements.txt", "manage.py", "pom.xml",
}


def _zip_category(path: Path) -> str | None:
    """Inspect ZIP member names without extracting any content."""
    if not zipfile.is_zipfile(path):
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            names = {Path(name).name for name in archive.namelist()[:5000] if name and not name.endswith("/")}
            if names & PROJECT_MARKERS:
                return "Archives/Projects"
            if any(name.lower().endswith((".csv", ".parquet", ".jsonl")) for name in names):
                return "Archives/Data"
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return None
    return None


def classify(path: Path, settings: Settings) -> str | None:
    """Return a relative destination folder, or None if no rule matches."""
    if path.is_dir():
        return "Projects"

    suffix = path.suffix.lower()
    guessed_mime, _ = mimetypes.guess_type(path.name)
    # Read only a small header for MIME sniffing; never execute downloaded content.
    try:
        with path.open("rb") as stream:
            header = stream.read(8192)
        if header.startswith(b"%PDF-"):
            guessed_mime = "application/pdf"
        elif header.startswith(b"PK\x03\x04"):
            guessed_mime = "application/zip"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            guessed_mime = "image/png"
        elif header.startswith(b"\xff\xd8\xff"):
            guessed_mime = "image/jpeg"
    except OSError:
        pass

    if suffix == ".zip":
        special = _zip_category(path)
        if special:
            return special

    for rule in settings.rules:
        extension_match = suffix in rule.extensions
        mime_match = bool(guessed_mime) and any(
            guessed_mime.lower().startswith(prefix) for prefix in rule.mime_prefixes
        )
        if extension_match or mime_match:
            return rule.folder

    return "Miscellaneous" if settings.organize_unknown else None
