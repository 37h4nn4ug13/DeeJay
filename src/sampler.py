"""Simple audio sampler with scheduling and voice management.

This module provides a :class:`Sampler` that can trigger sounds immediately
or quantized to a beat grid derived from an external deck clock. Sounds are
fetched from a SQLite ``sounds`` table and rendered with lightweight envelope
shaping to avoid clicks. Polyphony is handled via a voice allocator that will
steal the oldest voice when the limit is exceeded.
"""
from __future__ import annotations

import sqlite3
import struct
import time
from dataclasses import dataclass
from typing import Callable, List


@dataclass
class Sound:
    """Represents a decoded sample that can be triggered by the sampler."""

    id: int
    name: str
    sample_rate: int
    data: List[float]  # mono float samples in range [-1, 1]


class SoundRepository:
    """Loads sound data stored in a SQLite ``sounds`` table.

    The table is expected to expose ``id`` (INTEGER PRIMARY KEY), ``name``
    (TEXT), ``sample_rate`` (INTEGER) and ``data`` (BLOB) columns. The BLOB is
    assumed to contain raw little-endian float32 PCM samples.
    """

    def __init__(self, path: str) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, sound_id: int) -> Sound:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, sample_rate, data FROM sounds WHERE id = ?",
                (sound_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Sound with id {sound_id} not found")
            raw = row["data"]
            if len(raw) % 4 != 0:
                raise ValueError("Sound data is not valid little-endian float32 PCM")
            float_count = len(raw) // 4
            data = list(struct.unpack(f"<{float_count}f", raw))
            return Sound(
                id=row["id"],
                name=row["name"],
                sample_rate=row["sample_rate"],
                data=data,
            )


@dataclass
class DeckState:
    """Current tempo information used for beat-grid scheduling."""

    bpm: float
    phase: float  # 0.0-1.0 beat phase within current beat


@dataclass
class ScheduledTrigger:
    sound_id: int
    start_time: float


@dataclass
class Voice:
    sound: Sound
    start_time: float
    position: int = 0

    def is_finished(self) -> bool:
        return self.position >= len(self.sound.data)


class VoiceAllocator:
    """Manages polyphony limits and voice stealing."""

    def __init__(self, max_voices: int) -> None:
        self.max_voices = max_voices
        self.active: List[Voice] = []

    def allocate(self, sound: Sound, start_time: float) -> Voice:
        if len(self.active) >= self.max_voices:
            # Steal the oldest voice (FIFO) to guarantee deterministic behaviour.
            self.active.sort(key=lambda v: v.start_time)
            self.active.pop(0)
        voice = Voice(sound=sound, start_time=start_time)
        self.active.append(voice)
        return voice

    def remove_finished(self) -> None:
        self.active = [v for v in self.active if not v.is_finished()]


class Sampler:
    """A small offline-friendly sampler with beat scheduling and envelopes."""

    def __init__(
        self,
        repository: SoundRepository,
        sample_rate: int = 48000,
        max_voices: int = 8,
        attack_ms: float = 2.0,
        release_ms: float = 8.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.repository = repository
        self.sample_rate = sample_rate
        self.attack_samples = max(1, int(attack_ms * sample_rate / 1000))
        self.release_samples = max(1, int(release_ms * sample_rate / 1000))
        self.clock = clock
        self.allocator = VoiceAllocator(max_voices)
        self.scheduled: List[ScheduledTrigger] = []
        self._last_render_time = self.clock()

    def _now(self) -> float:
        return self.clock()

    def trigger_now(self, sound_id: int) -> None:
        self.schedule(sound_id, self._now())

    def trigger_on_grid(self, sound_id: int, deck: DeckState) -> float:
        """Schedule a trigger aligned to the next beat.

        Returns the absolute timestamp at which the sound will be started.
        """
        now = self._now()
        seconds_per_beat = 60.0 / max(deck.bpm, 1e-6)
        phase = deck.phase % 1.0
        time_until_next_beat = (1.0 - phase) * seconds_per_beat
        start_time = now + time_until_next_beat
        self.schedule(sound_id, start_time)
        return start_time

    def schedule(self, sound_id: int, start_time: float) -> None:
        self.scheduled.append(ScheduledTrigger(sound_id=sound_id, start_time=start_time))
        self.scheduled.sort(key=lambda t: t.start_time)

    def _activate_due_triggers(self, up_to_time: float) -> None:
        due: List[ScheduledTrigger] = []
        while self.scheduled and self.scheduled[0].start_time <= up_to_time:
            due.append(self.scheduled.pop(0))
        for trig in due:
            sound = self.repository.get(trig.sound_id)
            self.allocator.allocate(sound, trig.start_time)

    def render(self, duration: float) -> List[float]:
        """Advance the engine by ``duration`` seconds and return mixed audio.

        This offline render method is adequate for tests or non-realtime use.
        """
        end_time = self._last_render_time + duration
        buffer = [0.0 for _ in range(int(duration * self.sample_rate))]

        # Activate any triggers that occur within the window.
        self._activate_due_triggers(end_time)

        # Mix active voices.
        for voice in list(self.allocator.active):
            self._mix_voice(buffer, voice, window_start=self._last_render_time)
        self.allocator.remove_finished()

        self._last_render_time = end_time
        return buffer

    def _mix_voice(self, buffer: List[float], voice: Voice, window_start: float) -> None:
        samples_per_sec = self.sample_rate
        voice_start_index = max(0, int((voice.start_time - window_start) * samples_per_sec))
        if voice_start_index >= len(buffer):
            return

        buffer_index = voice_start_index
        sample_index = voice.position
        while buffer_index < len(buffer) and sample_index < len(voice.sound.data):
            raw_sample = voice.sound.data[sample_index]
            amplitude = self._envelope_gain(sample_index, len(voice.sound.data))
            buffer[buffer_index] += raw_sample * amplitude
            buffer_index += 1
            sample_index += 1

        voice.position = sample_index

    def _envelope_gain(self, index: int, total_length: int) -> float:
        # Attack
        if index < self.attack_samples:
            return index / float(self.attack_samples)
        # Release
        if index >= total_length - self.release_samples:
            remaining = total_length - index - 1
            return max(0.0, remaining / float(self.release_samples))
        return 1.0

    def clear(self) -> None:
        self.scheduled.clear()
        self.allocator.active.clear()
        self._last_render_time = self._now()


__all__ = [
    "DeckState",
    "Sampler",
    "Sound",
    "SoundRepository",
    "Voice",
]
