# DeeJay

Lightweight building blocks for DJ-style audio playback. The project includes:

- A **master clock** that tracks global buffer phase and alignment.
- **Deck** abstractions that load audio files, manage transport (play/pause/seek),
  and expose tempo/pitch controls.
- Minimal **DSP stubs** that record the tempo and pitch operations that would be
  applied to each processed buffer.

Run the test suite with `pytest` to verify deck alignment, scheduling, and DSP
wiring.
Audio processing scaffolding focused on time-stretching and pitch shifting.

## Building
```bash
cmake -B build -S . -DDEEJAY_ENABLE_RUBBERBAND=ON
cmake --build build
```
If the Rubber Band Library is unavailable, the code will fall back to a stub implementation so the rest of the engine can still compile.

## Components
- `TimeStretchPitchProcessor`: wraps Rubber Band (or a stub) to provide tempo and pitch control with endpoint descriptors for sliders and numeric inputs.
- `LatencyCompensatedProcessor`: adds latency-aware buffering and exposes UI-friendly control endpoints, including manual latency override.

## Validation
See `docs/validation_plan.md` for the manual test plan covering tempo/pitch sweeps and quality checks.

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
Lightweight tools for capturing the master mix output, saving straight to
WAV/FLAC via libsndfile, and pushing quick-save metadata into a SQLite
`sounds` table.

## Setup

Install dependencies (libsndfile is required for FLAC/WAV support):

```bash
python -m pip install -e .
```

## Recording & quick-save workflow

Record the master mix for a fixed window and persist metadata + waveform
preview in one step:

```bash
python -m deejay.cli 10 --format FLAC --title "Rehearsal take" \
  --output-dir recordings --db data/deejay.db
```

This will:

1. Capture 10 seconds from the default input device into `recordings/` as a
   libsndfile-backed FLAC.
2. Generate a 200-sample normalized waveform preview.
3. Insert the new take into the `sounds` table with the preview and timestamps.

Use `python -m deejay.cli --help` for additional options.
You can also use the entry point `deejay-cli` once installed.
An Electron + TypeScript shell for a dual-deck DJ interface with lock-free parameter queues and placeholder native engine bindings.

## Features
- Library browser that exposes track metadata and lets you load decks via click (Deck A) or context menu (Deck B).
- Dual decks with waveform displays rendered from cached data, plus tempo and pitch sliders.
- Crossfader, sampler pads, and recorder toggle wired to lock-free parameter queues for the native engine bindings.

## Development
1. Install dependencies:
   ```bash
   npm install
   ```
2. Build and launch Electron:
   ```bash
   npm start
   ```

The UI loads pre-generated waveform caches and routes UI events to `SharedArrayBuffer`-backed parameter queues so the audio engine can poll without locks.
Cross-platform helper for configuring device and buffer defaults with crash reporting, asset bundling, and simple versioning hooks.

## Features
- **Multi-platform builds** via `make build-linux`, `make build-macos`, and `make build-windows` targets.
- **Bundling** of assets and runtime dependencies into `dist/<target>/` using `make bundle` or `scripts/bundle.sh`.
- **Versioning** honors the `BUILD_VERSION` environment variable, otherwise falls back to the package version.
- **Crash reporting** installs a panic hook that writes to `crash.log` (configurable with `--crash-log`).
- **Settings persistence** keeps device and buffer configuration in `settings.json`.

## Getting Started
1. Install Rust (1.74+ recommended).
2. Build for your host platform:
   ```bash
   make build-linux  # or build-macos / build-windows
   ```
3. Bundle assets and runtime deps after building:
   ```bash
   make bundle
   ```
   Artifacts land in `dist/<target>/` with the binary, `assets/`, `runtime/`, and a seeded `settings.json`.

## Running
The CLI loads `settings.json` (creating defaults if missing), allows overrides, and can persist changes:
```bash
cargo run -- --device hw:0,0 --buffer-frames 1024 --sample-rate 48000 --save
```

### Bundling from the CLI
You can also drive bundling through the app itself once a release binary exists:
```bash
cargo run --release -- bundle --target x86_64-unknown-linux-gnu --binary target/x86_64-unknown-linux-gnu/release/deejay
```

## Version Overrides
Set `BUILD_VERSION` at build time to stamp binaries:
```bash
BUILD_VERSION=1.2.3 make build-linux
```

## Crash Reports
Crashes append to `crash.log` with timestamps and version metadata. Override the location with `--crash-log /tmp/deejay-crash.log`.

## Settings
`settings.json` stores device, buffer, and sample rate values. Use `--save` to persist overrides; otherwise values are applied transiently for the process.
