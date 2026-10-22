from pathlib import Path
import zipfile

from sortwise.classifier import classify
from sortwise.config import load_settings


def settings():
    return load_settings(Path(__file__).parents[1] / "config.toml")


def test_pdf_goes_to_pdf_folder(tmp_path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\nexample")
    assert classify(path, settings()) == "Documents/PDF"


def test_unknown_goes_to_miscellaneous(tmp_path):
    path = tmp_path / "mystery.unknownext"
    path.write_text("hello")
    assert classify(path, settings()) == "Miscellaneous"


def test_zip_project_is_detected_without_extracting(tmp_path):
    path = tmp_path / "project.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("demo/pyproject.toml", "[project]")
        archive.writestr("demo/main.py", "print('hello')")
    assert classify(path, settings()) == "Archives/Projects"
    assert path.exists()  # Inspection never extracts or removes the archive.


def test_directory_is_project(tmp_path):
    folder = tmp_path / "sample-project"
    folder.mkdir()
    assert classify(folder, settings()) == "Projects"
