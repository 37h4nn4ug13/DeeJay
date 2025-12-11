import os
import sqlite3
import struct
import tempfile
import unittest
from typing import List

from src.sampler import DeckState, Sampler, SoundRepository


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.time = start

    def __call__(self) -> float:  # pragma: no cover - trivial
        return self.time

    def advance(self, delta: float) -> None:
        self.time += delta


def create_repository(data: List[float], sample_rate: int = 48000) -> SoundRepository:
    fd, path = tempfile.mkstemp()
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE sounds (id INTEGER PRIMARY KEY, name TEXT, sample_rate INTEGER, data BLOB)"
    )
    payload = struct.pack(f"<{len(data)}f", *data)
    conn.execute(
        "INSERT INTO sounds (id, name, sample_rate, data) VALUES (?, ?, ?, ?)",
        (1, "kick", sample_rate, payload),
    )
    conn.commit()
    conn.close()
    return SoundRepository(path)


class SamplerTests(unittest.TestCase):
    def test_repository_loads_sound(self) -> None:
        samples = [1.0 for _ in range(16)]
        repo = create_repository(samples, sample_rate=44100)
        sound = repo.get(1)
        self.assertEqual(sound.name, "kick")
        self.assertEqual(sound.sample_rate, 44100)
        self.assertEqual(sound.data, samples)
        os.remove(repo.path)

    def test_trigger_on_grid_aligns_to_next_beat(self) -> None:
        clock = FakeClock(start=10.0)
        repo = create_repository([1.0 for _ in range(200)], sample_rate=1000)
        sampler = Sampler(repo, clock=clock, sample_rate=1000)
        start_time = sampler.trigger_on_grid(1, DeckState(bpm=120.0, phase=0.25))
        self.assertAlmostEqual(start_time, 10.375, places=6)
        buffer = sampler.render(0.4)
        self.assertGreater(sum(abs(v) for v in buffer), 0.0)
        os.remove(repo.path)

    def test_polyphony_steals_oldest_voice(self) -> None:
        clock = FakeClock(start=0.0)
        data = [1.0 for _ in range(50)]
        repo = create_repository(data, sample_rate=1000)
        sampler = Sampler(repo, max_voices=2, clock=clock, sample_rate=1000)
        sampler.schedule(1, start_time=0.0)
        sampler.schedule(1, start_time=0.01)
        sampler.schedule(1, start_time=0.02)
        sampler.render(0.03)
        active_starts = {voice.start_time for voice in sampler.allocator.active}
        self.assertEqual(len(active_starts), 2)
        self.assertNotIn(0.0, active_starts)
        os.remove(repo.path)

    def test_envelope_reduces_clicks(self) -> None:
        clock = FakeClock(start=0.0)
        data = [1.0 for _ in range(100)]
        repo = create_repository(data, sample_rate=1000)
        sampler = Sampler(repo, attack_ms=10, release_ms=10, sample_rate=1000, clock=clock)
        sampler.trigger_now(1)
        buffer = sampler.render(duration=len(data) / sampler.sample_rate)
        self.assertAlmostEqual(buffer[0], 0.0, places=5)
        self.assertAlmostEqual(buffer[-1], 0.0, places=5)
        self.assertGreater(buffer[5], buffer[1])
        os.remove(repo.path)


if __name__ == "__main__":
    unittest.main()
