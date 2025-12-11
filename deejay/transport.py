from __future__ import annotations

from typing import Protocol


class TransportController(Protocol):
    """Interface for actions driven by MIDI controls."""

    def toggle_play_pause(self, deck: str) -> None:
        ...

    def set_tempo(self, deck: str, value: float) -> None:
        ...

    def set_pitch(self, deck: str, value: float) -> None:
        ...

    def set_crossfader(self, value: float) -> None:
        ...

    def trigger_sampler(self, pad: int, velocity: int) -> None:
        ...
