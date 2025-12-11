"""Deck abstractions for loading and scheduling audio playback."""
from __future__ import annotations

import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .clock import MasterClock
from . import dsp


@dataclass
class TransportState:
    """Represents the externally visible state of a deck."""

    playing: bool
    position_seconds: float
    duration_seconds: float
    tempo_ratio: float
    pitch_semitones: float
    scheduled_start_frame: Optional[int]


@dataclass
class Deck:
    """A basic deck capable of loading and playing an audio file."""

    name: str
    clock: MasterClock
    audio_path: Optional[Path] = None
    total_frames: int = 0
    file_sample_rate: Optional[int] = None
    position_frames: int = 0
    playing: bool = False
    tempo_ratio: float = 1.0
    pitch_semitones: float = 0.0
    scheduled_start_frame: Optional[int] = None
    _last_dsp_result: Optional[dsp.DSPResult] = field(default=None, init=False, repr=False)

    def load(self, audio_file: Path) -> None:
        """Load an audio file and cache metadata."""

        with wave.open(str(audio_file), "rb") as handle:
            self.total_frames = handle.getnframes()
            self.file_sample_rate = handle.getframerate()
        self.audio_path = Path(audio_file)
        self.position_frames = 0
        self.playing = False
        self.scheduled_start_frame = None

    @property
    def duration_seconds(self) -> float:
        if not self.file_sample_rate:
            return 0.0
        return self.total_frames / float(self.file_sample_rate)

    def seek(self, seconds: float) -> None:
        frames = min(self.clock.seconds_to_frames(seconds), self.total_frames)
        self.position_frames = frames

    def play(self) -> int:
        """Schedule playback to start on the next buffer boundary."""

        self.playing = True
        self.scheduled_start_frame = self.clock.next_boundary()
        return self.scheduled_start_frame

    def pause(self) -> None:
        self.playing = False

    def stop(self) -> None:
        self.playing = False
        self.position_frames = 0
        self.scheduled_start_frame = None

    def process(self) -> Optional[dsp.DSPResult]:
        """Simulate buffer processing and advance transport state."""

        if not self.playing:
            return None

        if self.scheduled_start_frame is not None and self.clock.frame_counter < self.scheduled_start_frame:
            # Waiting for the boundary to arrive
            return None

        # Once we process the first buffer, clear the schedule flag
        if self.scheduled_start_frame is not None:
            self.scheduled_start_frame = None

        processed = dsp.process_buffer(self.clock.buffer_size, self.tempo_ratio, self.pitch_semitones)
        self.position_frames += processed.stretched_frames
        self.position_frames = min(self.position_frames, self.total_frames)
        self._last_dsp_result = processed

        if self.position_frames >= self.total_frames:
            self.playing = False

        return processed

    def transport_state(self) -> TransportState:
        return TransportState(
            playing=self.playing,
            position_seconds=self.clock.frames_to_seconds(self.position_frames),
            duration_seconds=self.duration_seconds,
            tempo_ratio=self.tempo_ratio,
            pitch_semitones=self.pitch_semitones,
            scheduled_start_frame=self.scheduled_start_frame,
        )

    def last_dsp_summary(self) -> Optional[str]:
        if self._last_dsp_result is None:
            return None
        return self._last_dsp_result.describe()
