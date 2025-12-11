import wave
from pathlib import Path

import pytest

from deejay.clock import MasterClock
from deejay.deck import Deck


def write_sine_stub(path: Path, frames: int = 4800, sample_rate: int = 48000):
    # Write silence for simplicity; content is irrelevant for metadata.
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames)


def test_master_clock_alignment():
    clock = MasterClock(sample_rate=48_000, buffer_size=512)
    clock.tick()  # advance one buffer
    assert clock.phase == 0

    clock.frame_counter = 100
    assert clock.phase == 100
    assert clock.next_boundary() == 512
    assert clock.align_frame(130) == 512


def test_deck_load_and_transport_state(tmp_path: Path):
    audio_path = tmp_path / "tone.wav"
    write_sine_stub(audio_path, frames=4800, sample_rate=48000)

    clock = MasterClock(sample_rate=48_000, buffer_size=256)
    deck = Deck(name="A", clock=clock)
    deck.load(audio_path)

    state = deck.transport_state()
    assert pytest.approx(state.duration_seconds, rel=1e-3) == deck.duration_seconds
    assert not state.playing
    assert state.position_seconds == 0


def test_play_aligns_to_buffer_and_processes(tmp_path: Path):
    audio_path = tmp_path / "tone.wav"
    write_sine_stub(audio_path, frames=1024, sample_rate=48000)

    clock = MasterClock(sample_rate=48_000, buffer_size=256)
    clock.frame_counter = 100  # simulate mid-buffer positioning
    deck = Deck(name="B", clock=clock)
    deck.load(audio_path)

    scheduled = deck.play()
    assert scheduled == clock.align_frame(clock.frame_counter)

    # Should wait until the scheduled boundary is reached
    assert deck.process() is None

    clock.frame_counter = scheduled
    result = deck.process()
    assert result is not None
    assert result.tempo_ratio == 1.0
    assert deck.transport_state().position_seconds > 0


def test_tempo_and_pitch_controls(tmp_path: Path):
    audio_path = tmp_path / "tone.wav"
    write_sine_stub(audio_path, frames=400, sample_rate=48000)

    clock = MasterClock(sample_rate=48_000, buffer_size=256)
    deck = Deck(name="C", clock=clock)
    deck.load(audio_path)

    deck.tempo_ratio = 1.5
    deck.pitch_semitones = -2.0

    scheduled = deck.play()
    clock.frame_counter = scheduled

    result = deck.process()
    assert result is not None
    assert result.tempo_ratio == 1.5
    assert result.pitch_semitones == -2.0
    assert any(op.name == "pitch" for op in result.operations)

    # Processing again should stop at the end of the short file
    clock.tick()
    deck.process()
    assert not deck.transport_state().playing
