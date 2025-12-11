from __future__ import annotations

import dataclasses
import datetime as dt
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_DB_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _utcnow_str() -> str:
    return dt.datetime.utcnow().strftime(_DB_ISO_FORMAT)


@dataclasses.dataclass
class Track:
    id: str
    title: str
    artist: str
    file_uuid: str
    file_path: str
    bpm: Optional[float]
    musical_key: Optional[str]
    intro_start: Optional[float]
    intro_end: Optional[float]
    outro_start: Optional[float]
    outro_end: Optional[float]
    cue_points: Optional[str]
    created_at: str
    updated_at: str
    analyzed_at: Optional[str]


class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def apply_migrations(self) -> None:
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
            )
            current_versions = {
                row[0] for row in conn.execute("SELECT version FROM schema_migrations")
            }
            for version, statements in MIGRATIONS:
                if version in current_versions:
                    continue
                with conn:
                    for stmt in statements:
                        conn.execute(stmt)
                    conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))

    def create_track(
        self,
        title: str,
        artist: str,
        file_path: str,
        bpm: Optional[float] = None,
        musical_key: Optional[str] = None,
        intro_start: Optional[float] = None,
        intro_end: Optional[float] = None,
        outro_start: Optional[float] = None,
        outro_end: Optional[float] = None,
        cue_points: Optional[str] = None,
    ) -> Track:
        track_id = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        now = _utcnow_str()
        with self.connect() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO tracks(id, title, artist, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (track_id, title, artist, now, now),
                )
                conn.execute(
                    """
                    INSERT INTO sounds(file_uuid, track_id, file_path, imported_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (file_uuid, track_id, file_path, now),
                )
                conn.execute(
                    """
                    INSERT INTO metadata(
                        track_id, bpm, musical_key, intro_start, intro_end, outro_start, outro_end, cue_points, analyzed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(track_id) DO UPDATE SET
                        bpm=excluded.bpm,
                        musical_key=excluded.musical_key,
                        intro_start=excluded.intro_start,
                        intro_end=excluded.intro_end,
                        outro_start=excluded.outro_start,
                        outro_end=excluded.outro_end,
                        cue_points=excluded.cue_points,
                        analyzed_at=excluded.analyzed_at
                    """,
                    (
                        track_id,
                        bpm,
                        musical_key,
                        intro_start,
                        intro_end,
                        outro_start,
                        outro_end,
                        cue_points,
                        now if bpm or musical_key or cue_points else None,
                    ),
                )
        return self.get_track(track_id)

    def get_track(self, track_id: str) -> Optional[Track]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    t.id,
                    t.title,
                    t.artist,
                    s.file_uuid,
                    s.file_path,
                    m.bpm,
                    m.musical_key,
                    m.intro_start,
                    m.intro_end,
                    m.outro_start,
                    m.outro_end,
                    m.cue_points,
                    t.created_at,
                    t.updated_at,
                    m.analyzed_at
                FROM tracks t
                JOIN sounds s ON s.track_id = t.id
                LEFT JOIN metadata m ON m.track_id = t.id
                WHERE t.id = ?
                """,
                (track_id,),
            ).fetchone()
            if not row:
                return None
            return Track(**row)

    def list_tracks(
        self,
        bpm_min: Optional[float] = None,
        bpm_max: Optional[float] = None,
        musical_key: Optional[str] = None,
    ) -> List[Track]:
        query = [
            "SELECT t.id, t.title, t.artist, s.file_uuid, s.file_path, m.bpm, m.musical_key, m.intro_start, m.intro_end, m.outro_start, m.outro_end, m.cue_points, t.created_at, t.updated_at, m.analyzed_at",
            "FROM tracks t",
            "JOIN sounds s ON s.track_id = t.id",
            "LEFT JOIN metadata m ON m.track_id = t.id",
            "WHERE 1=1",
        ]
        params: List[object] = []
        if bpm_min is not None:
            query.append("AND m.bpm >= ?")
            params.append(bpm_min)
        if bpm_max is not None:
            query.append("AND m.bpm <= ?")
            params.append(bpm_max)
        if musical_key is not None:
            query.append("AND m.musical_key = ?")
            params.append(musical_key)
        query.append("ORDER BY t.created_at DESC")
        sql = "\n".join(query)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [Track(**row) for row in rows]

    def update_track_metadata(
        self,
        track_id: str,
        *,
        bpm: Optional[float] = None,
        musical_key: Optional[str] = None,
        intro_start: Optional[float] = None,
        intro_end: Optional[float] = None,
        outro_start: Optional[float] = None,
        outro_end: Optional[float] = None,
        cue_points: Optional[str] = None,
    ) -> Optional[Track]:
        now = _utcnow_str()
        with self.connect() as conn:
            with conn:
                updated = conn.execute(
                    """
                    UPDATE metadata SET
                        bpm = COALESCE(?, bpm),
                        musical_key = COALESCE(?, musical_key),
                        intro_start = COALESCE(?, intro_start),
                        intro_end = COALESCE(?, intro_end),
                        outro_start = COALESCE(?, outro_start),
                        outro_end = COALESCE(?, outro_end),
                        cue_points = COALESCE(?, cue_points),
                        analyzed_at = ?
                    WHERE track_id = ?
                    """,
                    (
                        bpm,
                        musical_key,
                        intro_start,
                        intro_end,
                        outro_start,
                        outro_end,
                        cue_points,
                        now,
                        track_id,
                    ),
                )
                if updated.rowcount == 0:
                    return None
                conn.execute(
                    "UPDATE tracks SET updated_at = ? WHERE id = ?", (now, track_id)
                )
        return self.get_track(track_id)

    def delete_track(self, track_id: str) -> None:
        with self.connect() as conn:
            with conn:
                conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))


MIGRATIONS: Sequence[tuple[int, Sequence[str]]] = (
    (
        1,
        (
            """
            CREATE TABLE tracks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE sounds (
                file_uuid TEXT PRIMARY KEY,
                track_id TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                imported_at TEXT NOT NULL,
                FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE metadata (
                track_id TEXT PRIMARY KEY,
                bpm REAL,
                musical_key TEXT,
                intro_start REAL,
                intro_end REAL,
                outro_start REAL,
                outro_end REAL,
                cue_points TEXT,
                analyzed_at TEXT,
                FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX idx_metadata_bpm ON metadata(bpm)",
            "CREATE INDEX idx_metadata_key ON metadata(musical_key)",
        ),
    ),
)


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
