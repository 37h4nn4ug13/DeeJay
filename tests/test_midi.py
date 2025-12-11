import threading
import time
from pathlib import Path

from deejay.midi import MidiAction, MidiLearner, MidiMapping, MidiMappingStore, MidiMessage, MidiRouter


class RecordingController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def toggle_play_pause(self, deck: str) -> None:
        self.calls.append(("toggle", (deck,)))

    def set_tempo(self, deck: str, value: float) -> None:
        self.calls.append(("tempo", (deck, value)))

    def set_pitch(self, deck: str, value: float) -> None:
        self.calls.append(("pitch", (deck, value)))

    def set_crossfader(self, value: float) -> None:
        self.calls.append(("crossfader", (value,)))

    def trigger_sampler(self, pad: int, velocity: int) -> None:
        self.calls.append(("sampler", (pad, velocity)))


def test_learn_mode_persists_mapping(tmp_path: Path) -> None:
    db_path = tmp_path / "mappings.db"
    store = MidiMappingStore(db_path)
    learner = MidiLearner(store)
    learner.start_binding(MidiAction.PLAY_DECK_A)
    message = MidiMessage("note_on", channel=1, control=24, value=100)

    mapping = learner.process(message)

    assert mapping is not None
    loaded = store.get_mapping("note_on", 1, 24)
    assert loaded == mapping


def test_router_dispatches_on_realtime_thread(tmp_path: Path) -> None:
    controller = RecordingController()
    store = MidiMappingStore(tmp_path / "mappings.db")
    store.save_mapping(
        MidiMapping(
            message_type="control_change",
            channel=0,
            control=10,
            action=MidiAction.CROSSFADER,
        )
    )
    router = MidiRouter(controller, store)

    router.start()
    router.enqueue(MidiMessage("control_change", channel=0, control=10, value=100))
    time.sleep(0.1)
    router.stop()

    assert controller.calls[-1][0] == "crossfader"
    assert 0.0 <= controller.calls[-1][1][0] <= 1.0


def test_router_uses_learn_mode_when_no_mapping(tmp_path: Path) -> None:
    controller = RecordingController()
    store = MidiMappingStore(tmp_path / "mappings.db")
    learner = MidiLearner(store)
    router = MidiRouter(controller, store, learner=learner)
    learner.start_binding(MidiAction.SAMPLER_PAD, target="3")

    router.start()
    router.enqueue(MidiMessage("note_on", channel=1, control=60, value=90))
    time.sleep(0.1)
    router.stop()

    assert store.get_mapping("note_on", 1, 60)
    assert controller.calls[-1] == ("sampler", (3, 90))
