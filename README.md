# DeeJay

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
