"""Master clock and phase tracking utilities."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MasterClock:
    """Tracks the global transport phase in frames."""

    sample_rate: int = 48_000
    buffer_size: int = 512
    frame_counter: int = 0

    def tick(self, buffers: int = 1) -> int:
        """Advance the master clock by one or more buffers."""

        self.frame_counter += self.buffer_size * buffers
        return self.frame_counter

    @property
    def phase(self) -> int:
        """Current offset inside the active buffer."""

        return self.frame_counter % self.buffer_size

    def next_boundary(self) -> int:
        """Frame number of the next buffer boundary."""

        if self.phase == 0:
            return self.frame_counter
        return self.frame_counter + (self.buffer_size - self.phase)

    def align_frame(self, frame: int) -> int:
        """Snap an arbitrary frame count up to the next buffer boundary."""

        remainder = frame % self.buffer_size
        if remainder == 0:
            return frame
        return frame + (self.buffer_size - remainder)

    def seconds_to_frames(self, seconds: float) -> int:
        return int(seconds * self.sample_rate)

    def frames_to_seconds(self, frames: int) -> float:
        return frames / self.sample_rate
