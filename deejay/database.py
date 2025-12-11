"""SQLite-backed storage for track analysis outputs."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS track_analysis (
    track_id TEXT PRIMARY KEY,
    waveform_path TEXT,
    peaks_path TEXT,
    beatgrid_path TEXT,
    status TEXT,
    updated_at TEXT
);
"""


class AnalysisDatabase:
    """Lightweight wrapper around SQLite for persisting analysis results."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def upsert_analysis(
        self,
        track_id: str,
        *,
        waveform_path: Optional[Path] = None,
        peaks_path: Optional[Path] = None,
        beatgrid_path: Optional[Path] = None,
        status: str = "ready",
        updated_at: Optional[str] = None,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO track_analysis (track_id, waveform_path, peaks_path, beatgrid_path, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(track_id) DO UPDATE SET
                    waveform_path=excluded.waveform_path,
                    peaks_path=excluded.peaks_path,
                    beatgrid_path=excluded.beatgrid_path,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    track_id,
                    str(waveform_path) if waveform_path else None,
                    str(peaks_path) if peaks_path else None,
                    str(beatgrid_path) if beatgrid_path else None,
                    status,
                    updated_at,
                ),
            )
            conn.commit()

    def get_analysis(self, track_id: str) -> Optional[Dict[str, Optional[str]]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT track_id, waveform_path, peaks_path, beatgrid_path, status, updated_at FROM track_analysis WHERE track_id=?",
                (track_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "track_id": row[0],
                "waveform_path": row[1],
                "peaks_path": row[2],
                "beatgrid_path": row[3],
                "status": row[4],
                "updated_at": row[5],
            }

    def list_all(self) -> Dict[str, Dict[str, Optional[str]]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT track_id, waveform_path, peaks_path, beatgrid_path, status, updated_at FROM track_analysis"
            )
            results = {}
            for row in cursor.fetchall():
                results[row[0]] = {
                    "track_id": row[0],
                    "waveform_path": row[1],
                    "peaks_path": row[2],
                    "beatgrid_path": row[3],
                    "status": row[4],
                    "updated_at": row[5],
                }
            return results
