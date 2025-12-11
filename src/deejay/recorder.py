"""Audio recording utilities for capturing the master mix output.

This module streams PCM data from the default input device and writes it
out using libsndfile-backed formats (WAV/FLAC). It also computes a compact
waveform preview to support quick saving in the database layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal

import numpy as np
import sounddevice as sd
import soundfile as sf


SupportedFormat = Literal["WAV", "FLAC"]


@dataclass
class RecordingResult:
    """Container for recording metadata and preview information."""

    file_path: Path
    sample_rate: int
    channels: int
    duration: float
    audio_format: SupportedFormat
    preview: List[float]


class MasterMixRecorder:
    """Tap the master mix output into a recorder.

    The recorder uses the default input device, which can be configured via
    the operating system. Audio is captured in floating point and written
    with libsndfile through :mod:`soundfile`.
    """

    def __init__(self, sample_rate: int = 48_000, channels: int = 2) -> None:
        self.sample_rate = sample_rate
        self.channels = channels

    def _compute_preview(self, frames: np.ndarray, buckets: int = 200) -> List[float]:
        """Compute a compact waveform preview from the recorded audio.

        The preview stores peak-normalized absolute amplitudes for a fixed
        number of buckets, which keeps storage light while still giving a
        sense of the recording's shape.
        """

        if frames.size == 0:
            return [0.0] * buckets

        mono = frames.mean(axis=1) if frames.ndim > 1 else frames
        splits = np.array_split(mono, buckets)
        peaks = np.array([np.max(np.abs(chunk)) if chunk.size else 0.0 for chunk in splits])

        max_peak = float(peaks.max()) if peaks.size else 0.0
        if max_peak == 0.0:
            return [0.0] * buckets

        normalized = (peaks / max_peak).tolist()
        return [float(value) for value in normalized]

    def record(self, duration_seconds: float, output_path: Path, audio_format: SupportedFormat = "WAV") -> RecordingResult:
        """Record audio for a duration and write it to disk.

        Parameters
        ----------
        duration_seconds:
            Length of the capture window in seconds.
        output_path:
            Destination path for the recorded file. Parent directories will be created.
        audio_format:
            File format to use. Must be a libsndfile-supported container.
        """

        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        output_path = output_path.expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration_seconds * self.sample_rate)
        frames = sd.rec(
            total_frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
        )
        sd.wait()

        with sf.SoundFile(
            output_path,
            mode="w",
            samplerate=self.sample_rate,
            channels=self.channels,
            format=audio_format,
        ) as sink:
            sink.write(frames)

        preview = self._compute_preview(frames)
        return RecordingResult(
            file_path=output_path,
            sample_rate=self.sample_rate,
            channels=self.channels,
            duration=duration_seconds,
            audio_format=audio_format,
            preview=preview,
        )
