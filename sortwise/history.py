from __future__ import annotations

import sqlite3
from pathlib import Path


class History:
    def __init__(self, database: Path):
        database.parent.mkdir(parents=True, exist_ok=True)
        self.database = database
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT NOT NULL,
                    moved_path TEXT NOT NULL,
                    moved_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    undone_at TEXT,
                    status TEXT NOT NULL DEFAULT 'moved'
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def record_move(self, original: Path, moved: Path) -> int:
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO moves(original_path, moved_path) VALUES (?, ?)",
                (str(original), str(moved)),
            )
            return int(cur.lastrowid)

    def latest(self, move_id: int | None = None):
        with self._connect() as db:
            if move_id is None:
                return db.execute(
                    "SELECT * FROM moves WHERE status='moved' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            return db.execute(
                "SELECT * FROM moves WHERE id=? AND status='moved'", (move_id,)
            ).fetchone()

    def mark_undone(self, move_id: int) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE moves SET status='undone', undone_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                (move_id,),
            )

    def list_recent(self, limit: int = 20):
        with self._connect() as db:
            return db.execute(
                "SELECT * FROM moves ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
