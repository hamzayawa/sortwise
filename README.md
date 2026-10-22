# SortWise

A safe, configurable Downloads organizer for Ubuntu/Linux.

## Features in this first version

- Watches the top level of `~/Downloads` for new files and directories.
- Waits for file size/mtime to stabilize before moving.
- Ignores common incomplete-download suffixes such as `.crdownload` and `.part`.
- Classifies by configured extension rules and MIME hints.
- Inspects ZIP member names (without extracting) to recognize project and data archives.
- Moves into `~/Downloads/Organized/`.
- Avoids overwriting existing files by adding ` (1)`, ` (2)`, etc.
- Records moves in SQLite and supports undo.
- Has unit tests for classification, duplicate handling, partial downloads and undo.

## Install on Ubuntu

Python 3.11+ is required (Ubuntu 24.04 includes Python 3.12).

```bash
cd sortwise
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest
```

If your Python installation reports that `venv` is missing, install it with:

```bash
sudo apt update
sudo apt install python3-venv
```

## Run it

From the project directory with the virtual environment active:

```bash
sortwise --config ./config.toml watch
```

Stop it with `Ctrl+C`.

Organize items already in Downloads:

```bash
sortwise --config ./config.toml organize-existing
```

View history and undo the latest move:

```bash
sortwise --config ./config.toml history
sortwise --config ./config.toml undo
```

Undo a specific history entry:

```bash
sortwise --config ./config.toml undo --id 12
```

## Configuration

Edit `config.toml`. Rules are evaluated in order. Each rule may match extensions or MIME prefixes and maps to a relative folder under `Organized/`.

`organize_unknown = true` moves unmatched files to `Miscellaneous/`. Set it to `false` to leave them in Downloads.

Keep `destination` different from `watch`. Never set the destination to `/` or your home directory.

## Important limitations in v0.1

- Monitoring is top-level only; it does not recursively monitor nested directories.
- MIME detection is deliberately lightweight and does not depend on external `file`/libmagic.
- ZIP inspection reads filenames only and never extracts files.
- A filesystem event can be missed if SortWise is not running. Use `organize-existing` to process files that arrived while it was stopped.
- Undo refuses to overwrite an item if the original path has been reused.
- This is a first working version, not yet a hardened system service. Test it on sample files before relying on it for important data.
