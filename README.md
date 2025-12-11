# DeeJay

Lightweight building blocks for DJ-style audio playback. The project includes:

- A **master clock** that tracks global buffer phase and alignment.
- **Deck** abstractions that load audio files, manage transport (play/pause/seek),
  and expose tempo/pitch controls.
- Minimal **DSP stubs** that record the tempo and pitch operations that would be
  applied to each processed buffer.

Run the test suite with `pytest` to verify deck alignment, scheduling, and DSP
wiring.
