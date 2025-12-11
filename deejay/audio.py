"""Minimal audio engine façade that defers heavy work to background tasks."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .analysis import BackgroundAnalyzer, AnalysisResult


class AudioEngine:
    """Represents the time-sensitive audio thread entry points.

    Heavy analysis work is delegated to ``BackgroundAnalyzer`` so the audio
    thread remains responsive.
    """

    def __init__(self, analyzer: Optional[BackgroundAnalyzer] = None) -> None:
        self.analyzer = analyzer or BackgroundAnalyzer()

    def prime_track(self, track_id: str, audio_path: Path):
        """Kick off waveform and beat analysis without blocking playback."""
        future = self.analyzer.analyze_track(track_id, Path(audio_path))
        return future

    def shutdown(self) -> None:
        self.analyzer.shutdown()
