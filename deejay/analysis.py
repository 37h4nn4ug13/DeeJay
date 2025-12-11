"""Background analysis tasks for generating cached audio metadata."""
from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .database import AnalysisDatabase


@dataclass
class AnalysisResult:
    track_id: str
    waveform_path: Path
    peaks_path: Path
    beatgrid_path: Path
    updated_at: datetime


class CacheLayout:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_track_dir(self, track_id: str) -> Path:
        track_dir = self.base_dir / track_id
        track_dir.mkdir(parents=True, exist_ok=True)
        return track_dir

    def waveform_path(self, track_id: str) -> Path:
        return self.ensure_track_dir(track_id) / "waveform.json"

    def peaks_path(self, track_id: str) -> Path:
        return self.ensure_track_dir(track_id) / "peaks.json"

    def beatgrid_path(self, track_id: str) -> Path:
        return self.ensure_track_dir(track_id) / "beatgrid.json"


class BackgroundAnalyzer:
    """Coordinates background analysis jobs and caches their outputs."""

    def __init__(
        self,
        cache_dir: Path = Path("cache"),
        db_path: Path = Path("data/analysis.sqlite"),
        max_workers: int = 4,
    ) -> None:
        self.cache_layout = CacheLayout(cache_dir)
        self.db = AnalysisDatabase(db_path)
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="analysis")
        self._lock = threading.Lock()
        self._futures: Dict[str, Future[AnalysisResult]] = {}

    def analyze_track(self, track_id: str, audio_path: Path) -> Future[AnalysisResult]:
        """Schedule waveform, peaks, and beat grid analysis for a track.

        The method returns immediately with a future so the caller (e.g., the
        audio playback thread) is never blocked by heavy work.
        """
        cached = self._load_cached(track_id)
        if cached:
            future: Future[AnalysisResult] = Future()
            future.set_result(cached)
            return future

        with self._lock:
            existing = self._futures.get(track_id)
            if existing and not existing.done():
                return existing
            future = self.executor.submit(self._run_analysis, track_id, Path(audio_path))
            self._futures[track_id] = future
            return future

    def _load_cached(self, track_id: str) -> Optional[AnalysisResult]:
        record = self.db.get_analysis(track_id)
        if not record:
            return None
        waveform_path = Path(record["waveform_path"])
        peaks_path = Path(record["peaks_path"])
        beatgrid_path = Path(record["beatgrid_path"])
        if not (waveform_path.exists() and peaks_path.exists() and beatgrid_path.exists()):
            return None
        updated_at = datetime.fromisoformat(record["updated_at"]) if record["updated_at"] else datetime.utcnow()
        return AnalysisResult(
            track_id=track_id,
            waveform_path=waveform_path,
            peaks_path=peaks_path,
            beatgrid_path=beatgrid_path,
            updated_at=updated_at,
        )

    def _run_analysis(self, track_id: str, audio_path: Path) -> AnalysisResult:
        cache_dir = self.cache_layout.ensure_track_dir(track_id)
        raw_bytes = audio_path.read_bytes()

        waveform_data = self._compute_waveform(raw_bytes)
        waveform_path = self.cache_layout.waveform_path(track_id)
        waveform_path.write_text(json.dumps(waveform_data))

        peaks_data = self._compute_peaks(waveform_data)
        peaks_path = self.cache_layout.peaks_path(track_id)
        peaks_path.write_text(json.dumps(peaks_data))

        beatgrid_data = self._compute_beatgrid(raw_bytes)
        beatgrid_path = self.cache_layout.beatgrid_path(track_id)
        beatgrid_path.write_text(json.dumps(beatgrid_data))

        updated_at = datetime.utcnow()
        self.db.upsert_analysis(
            track_id,
            waveform_path=waveform_path,
            peaks_path=peaks_path,
            beatgrid_path=beatgrid_path,
            updated_at=updated_at.isoformat(),
        )
        return AnalysisResult(
            track_id=track_id,
            waveform_path=waveform_path,
            peaks_path=peaks_path,
            beatgrid_path=beatgrid_path,
            updated_at=updated_at,
        )

    @staticmethod
    def _compute_waveform(raw_bytes: bytes) -> Dict[str, object]:
        """Derive a deterministic pseudo-waveform from the file bytes."""
        digest = hashlib.sha256(raw_bytes).digest()
        amplitudes = [int(b) - 128 for b in digest]
        samples = [sum(amplitudes[i : i + 4]) for i in range(0, len(amplitudes), 4)]
        normalized = [round(val / max(1, max(abs(v) for v in samples)), 3) for val in samples]
        return {"amplitudes": normalized, "length": len(raw_bytes)}

    @staticmethod
    def _compute_peaks(waveform_data: Dict[str, object]) -> Dict[str, object]:
        values = waveform_data.get("amplitudes", [])
        window = 4
        peaks = [max(values[i : i + window], default=0) for i in range(0, len(values), window)]
        return {"peaks": peaks, "windows": window}

    @staticmethod
    def _compute_beatgrid(raw_bytes: bytes) -> Dict[str, object]:
        digest = hashlib.md5(raw_bytes).hexdigest()
        tempo_seed = int(digest[:4], 16)
        tempo = 80 + (tempo_seed % 60)  # bpm between 80-139
        beat_interval_sec = 60.0 / tempo
        grid = [round(i * beat_interval_sec, 3) for i in range(32)]
        return {"tempo": tempo, "beat_grid": grid}

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

