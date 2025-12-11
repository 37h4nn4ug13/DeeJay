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
