"""SQLite persistence layer for recorded sounds."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .recorder import RecordingResult


SCHEMA = """
CREATE TABLE IF NOT EXISTS sounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    format TEXT NOT NULL,
    sample_rate INTEGER NOT NULL,
    channels INTEGER NOT NULL,
    duration REAL NOT NULL,
    preview TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class SoundStore:
    """Wrap SQLite operations for quick-save workflows."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def insert_sound(self, recording: RecordingResult, title: Optional[str] = None) -> int:
        """Persist the recording with generated metadata and waveform preview.

        Parameters
        ----------
        recording:
            The recorded audio and preview data.
        title:
            Optional human-friendly label. When omitted a timestamp-based
            name is generated.
        """

        preview_blob = json.dumps(recording.preview)
        created = datetime.utcnow().isoformat()

        display_title = title or recording.file_path.stem
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sounds (title, file_path, format, sample_rate, channels, duration, preview, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    display_title,
                    str(recording.file_path),
                    recording.audio_format,
                    recording.sample_rate,
                    recording.channels,
                    recording.duration,
                    preview_blob,
                    created,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def fetch_recent(self, limit: int = 10) -> list[dict]:
        """Return the most recently saved sounds."""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM sounds ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
