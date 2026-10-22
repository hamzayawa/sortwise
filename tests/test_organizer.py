from pathlib import Path

from sortwise.config import load_settings
from sortwise.history import History
from sortwise.organizer import Organizer


def make_organizer(tmp_path):
    config_path = Path(__file__).parents[1] / "config.toml"
    settings = load_settings(config_path)
    # Rebuild immutable settings with isolated temporary paths for tests.
    from dataclasses import replace
    settings = replace(
        settings,
        watch=tmp_path / "Downloads",
        destination=tmp_path / "Downloads" / "Organized",
        database=tmp_path / "history.sqlite3",
        stable_seconds=0,
        poll_interval_seconds=0.2,
    )
    history = History(settings.database)
    return Organizer(settings, history), history


def test_moves_pdf_and_undoes_without_overwrite(tmp_path):
    organizer, history = make_organizer(tmp_path)
    source = organizer.settings.watch / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\nsample")

    moved = organizer.organize(source, wait_for_stability=False)
    assert moved == organizer.settings.destination / "Documents" / "PDF" / "paper.pdf"
    assert not source.exists()
    assert moved.exists()

    assert organizer.undo()
    assert source.exists()
    assert not moved.exists()
    assert history.latest() is None


def test_duplicate_name_is_not_overwritten(tmp_path):
    organizer, _ = make_organizer(tmp_path)
    source = organizer.settings.watch / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\nnew")
    destination_dir = organizer.settings.destination / "Documents" / "PDF"
    destination_dir.mkdir(parents=True)
    existing = destination_dir / "paper.pdf"
    existing.write_bytes(b"existing")

    moved = organizer.organize(source, wait_for_stability=False)
    assert moved == destination_dir / "paper (1).pdf"
    assert existing.read_bytes() == b"existing"
    assert moved.read_bytes() == b"%PDF-1.4\nnew"


def test_partial_download_is_ignored(tmp_path):
    organizer, _ = make_organizer(tmp_path)
    source = organizer.settings.watch / "paper.pdf.crdownload"
    source.write_bytes(b"partial")
    assert organizer.organize(source, wait_for_stability=False) is None
    assert source.exists()


def test_existing_original_blocks_undo(tmp_path):
    organizer, _ = make_organizer(tmp_path)
    source = organizer.settings.watch / "paper.pdf"
    source.write_bytes(b"%PDF-1.4\noriginal")
    moved = organizer.organize(source, wait_for_stability=False)
    assert moved is not None

    source.write_bytes(b"new file")
    assert organizer.undo() is False
    assert source.read_bytes() == b"new file"
    assert moved.exists()
