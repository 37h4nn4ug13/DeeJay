# DeeJay

MIDI handling utilities for routing deck controls, mixer changes, and sampler pads.

## Features

- Realtime MIDI router that runs on its own thread and dispatches to a `TransportController` interface.
- Learn mode that listens for the next MIDI CC/note and binds it to the requested action.
- SQLite-backed mapping store so learned bindings persist between sessions.

## Usage

```python
from deejay.midi import MidiAction, MidiLearner, MidiMappingStore, MidiMessage, MidiRouter
from deejay.transport import TransportController

# Implement the controller to drive your deck engine
class Engine(TransportController):
    ...

store = MidiMappingStore("~/deejay/mappings.db")
controller = Engine()
router = MidiRouter(controller, store)
router.start()

# Learn mode example
router.learner.start_binding(MidiAction.PLAY_DECK_A)
router.enqueue(MidiMessage("note_on", channel=1, control=24, value=100))
```
