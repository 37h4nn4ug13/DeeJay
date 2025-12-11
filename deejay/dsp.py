"""Lightweight DSP stubs used by the deck transport layer.

These helpers do not perform real audio processing. They simply return
metadata that higher-level components can use to confirm that a tempo or
pitch operation would be applied to a buffer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DSPOperation:
    """Represents an operation that would be performed on a buffer."""

    name: str
    value: float


@dataclass
class DSPResult:
    """Metadata describing how a buffer would be transformed."""

    source_frames: int
    tempo_ratio: float
    pitch_semitones: float
    stretched_frames: int
    operations: List[DSPOperation]

    def describe(self) -> str:
        steps = ", ".join(f"{op.name}={op.value}" for op in self.operations)
        return f"frames={self.source_frames} -> {self.stretched_frames} ({steps})"


def time_stretch(frames: int, ratio: float) -> DSPResult:
    """Pretend to time-stretch a buffer.

    The number of frames is scaled by the tempo ratio purely for metadata
    purposes. This does not process audio data.
    """

    stretched = int(frames * ratio)
    return DSPResult(
        source_frames=frames,
        tempo_ratio=ratio,
        pitch_semitones=0.0,
        stretched_frames=stretched,
        operations=[DSPOperation(name="tempo", value=ratio)],
    )


def pitch_shift(frames: int, semitones: float) -> DSPResult:
    """Pretend to pitch-shift a buffer.

    Pitch does not alter frame count in this stub, but we record the desired
    semitone shift.
    """

    return DSPResult(
        source_frames=frames,
        tempo_ratio=1.0,
        pitch_semitones=semitones,
        stretched_frames=frames,
        operations=[DSPOperation(name="pitch", value=semitones)],
    )


def process_buffer(frames: int, tempo_ratio: float, pitch_semitones: float) -> DSPResult:
    """Apply both tempo and pitch transforms to a buffer stub."""

    stretched = time_stretch(frames, tempo_ratio)
    # propagate pitch to the result while keeping stretched frame count
    operations = stretched.operations + [DSPOperation(name="pitch", value=pitch_semitones)]
    return DSPResult(
        source_frames=frames,
        tempo_ratio=tempo_ratio,
        pitch_semitones=pitch_semitones,
        stretched_frames=stretched.stretched_frames,
        operations=operations,
    )
