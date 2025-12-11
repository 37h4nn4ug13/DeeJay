from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import SimpleQueue
from typing import Callable, Iterable, Optional

from .transport import TransportController


@dataclass(frozen=True)
class MidiMessage:
    """A normalized representation of a MIDI message."""

    message_type: str  # "note_on" or "control_change"
    channel: int
    control: int  # note number or CC number
    value: int


@dataclass(frozen=True)
class MidiMapping:
    """Mapping of a MIDI control to an application action."""

    message_type: str
    channel: int
    control: int
    action: str
    target: Optional[str] = None


class MidiAction:
    PLAY_DECK_A = "play_deck_a"
    PLAY_DECK_B = "play_deck_b"
    TEMPO_DECK_A = "tempo_deck_a"
    TEMPO_DECK_B = "tempo_deck_b"
    PITCH_DECK_A = "pitch_deck_a"
    PITCH_DECK_B = "pitch_deck_b"
    CROSSFADER = "crossfader"
    SAMPLER_PAD = "sampler_pad"


class MidiMappingStore:
    """Persist mappings in a SQLite database."""

    def __init__(self, db_path: Path | str = "midi_mappings.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS midi_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_type TEXT NOT NULL,
                    channel INTEGER NOT NULL,
                    control INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    UNIQUE(message_type, channel, control)
                )
                """
            )
            conn.commit()

    def save_mapping(self, mapping: MidiMapping) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO midi_mappings(message_type, channel, control, action, target)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(message_type, channel, control)
                DO UPDATE SET action=excluded.action, target=excluded.target
                """,
                (
                    mapping.message_type,
                    mapping.channel,
                    mapping.control,
                    mapping.action,
                    mapping.target,
                ),
            )
            conn.commit()

    def delete_mapping(self, message_type: str, channel: int, control: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM midi_mappings WHERE message_type=? AND channel=? AND control=?",
                (message_type, channel, control),
            )
            conn.commit()

    def get_mapping(self, message_type: str, channel: int, control: int) -> Optional[MidiMapping]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT message_type, channel, control, action, target FROM midi_mappings WHERE message_type=? AND channel=? AND control=?",
                (message_type, channel, control),
            ).fetchone()
            if not row:
                return None
            return MidiMapping(*row)

    def load_all(self) -> list[MidiMapping]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT message_type, channel, control, action, target FROM midi_mappings"
            ).fetchall()
            return [MidiMapping(*row) for row in rows]


class MidiLearner:
    """Bind incoming MIDI messages to actions while learn mode is active."""

    def __init__(self, mapping_store: MidiMappingStore) -> None:
        self.mapping_store = mapping_store
        self._pending_action: Optional[str] = None
        self._pending_target: Optional[str] = None
        self._lock = threading.Lock()

    def start_binding(self, action: str, target: Optional[str] = None) -> None:
        with self._lock:
            self._pending_action = action
            self._pending_target = target

    def cancel(self) -> None:
        with self._lock:
            self._pending_action = None
            self._pending_target = None

    def process(self, message: MidiMessage) -> Optional[MidiMapping]:
        with self._lock:
            if not self._pending_action:
                return None
            mapping = MidiMapping(
                message_type=message.message_type,
                channel=message.channel,
                control=message.control,
                action=self._pending_action,
                target=self._pending_target,
            )
            self.mapping_store.save_mapping(mapping)
            self._pending_action = None
            self._pending_target = None
            return mapping


class MidiRouter:
    """Routes MIDI messages on a realtime thread to transport actions."""

    def __init__(
        self,
        controller: TransportController,
        mapping_store: MidiMappingStore,
        message_source: Callable[[], Iterable[MidiMessage]] | None = None,
        learner: Optional[MidiLearner] = None,
    ) -> None:
        self.controller = controller
        self.mapping_store = mapping_store
        self.message_source = message_source
        self.learner = learner or MidiLearner(mapping_store)
        self._queue: SimpleQueue[MidiMessage] = SimpleQueue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def enqueue(self, message: MidiMessage) -> None:
        self._queue.put(message)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self) -> None:
        for message in self._message_iterator():
            if self._stop_event.is_set():
                break
            self._handle_message(message)

    def _message_iterator(self) -> Iterable[MidiMessage]:
        if self.message_source is not None:
            yield from self.message_source()
            return
        while not self._stop_event.is_set():
            message = self._queue.get()
            yield message

    def _handle_message(self, message: MidiMessage) -> None:
        mapping = self.mapping_store.get_mapping(
            message.message_type, message.channel, message.control
        )
        if not mapping:
            mapping = self.learner.process(message)
            if not mapping:
                return
        self._dispatch(mapping, message)

    def _dispatch(self, mapping: MidiMapping, message: MidiMessage) -> None:
        action = mapping.action
        if action == MidiAction.PLAY_DECK_A:
            self.controller.toggle_play_pause("A")
        elif action == MidiAction.PLAY_DECK_B:
            self.controller.toggle_play_pause("B")
        elif action == MidiAction.TEMPO_DECK_A:
            self.controller.set_tempo("A", self._normalize_slider(message.value))
        elif action == MidiAction.TEMPO_DECK_B:
            self.controller.set_tempo("B", self._normalize_slider(message.value))
        elif action == MidiAction.PITCH_DECK_A:
            self.controller.set_pitch("A", self._normalize_pitch(message.value))
        elif action == MidiAction.PITCH_DECK_B:
            self.controller.set_pitch("B", self._normalize_pitch(message.value))
        elif action == MidiAction.CROSSFADER:
            self.controller.set_crossfader(self._normalize_slider(message.value))
        elif action == MidiAction.SAMPLER_PAD:
            pad_index = int(mapping.target or 0)
            self.controller.trigger_sampler(pad_index, message.value)

    @staticmethod
    def _normalize_slider(value: int) -> float:
        return max(0.0, min(1.0, value / 127.0))

    @staticmethod
    def _normalize_pitch(value: int) -> float:
        return (value - 64) / 64.0
