# DeeJay

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
