# DeeJay

A lightweight Rust mixing core that sums two stereo decks with an equal-power
crossfader, per-deck gain, and a master output gain. Parameter changes are sent
from a control thread over a lock-free queue so the audio thread can stay
real-time and avoid locks.

## Features

- Equal-power crossfader to smoothly blend deck A and deck B.
- Independent gain control for each deck and a master gain stage.
- Lock-free parameter queue using `crossbeam_queue::ArrayQueue` for safe control
  surface updates from other threads.
- Simple stereo mixing API with tests demonstrating the gain staging order.

## Usage

```rust
use deejay::{parameter_channel, DeckId, ParameterUpdate, SummingBus};

let (sender, receiver) = parameter_channel(32);
let mut bus = SummingBus::new(receiver);

// Control thread pushes updates without blocking the audio callback.
sender
    .send(ParameterUpdate::Crossfader(0.5))
    .expect("queue has capacity");
sender
    .send(ParameterUpdate::DeckGain { deck: DeckId::A, gain: 0.8 })
    .expect("queue has capacity");

// Audio thread mixes stereo frames.
let deck_a = vec![0.0_f32; 128];
let deck_b = vec![0.0_f32; 128];
let mut output = vec![0.0_f32; 128];
bus.mix_stereo(&deck_a, &deck_b, &mut output);
```
