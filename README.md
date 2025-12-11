# DeeJay

SQLite-backed catalog for tracks, sounds, and metadata with a minimal CLI.

## Database schema

Migrations create three primary tables:

- `tracks`: logical track entries (UUID id, title, artist, timestamps)
- `sounds`: UUID-based audio file references tied to tracks
- `metadata`: BPM/key markers plus intro/outro positions and cue points

Run migrations at any time; they are idempotent and recorded in `schema_migrations`.

```bash
python -m deejay.cli --db deejay.db migrate
```

## Importing audio files

Import files and auto-generate deterministic placeholder metadata (BPM, key, markers, cue points) based on the file path.

```bash
python -m deejay.cli --db deejay.db import ~/music/track.wav --title "My Track" --artist "DJ Example"
```

The command returns the created track, including the UUID-based file reference.

## Querying and CRUD

Fetch, query, update, or delete tracks using the CLI:

```bash
# Get by ID
python -m deejay.cli --db deejay.db get <track_id>

# Filter by BPM range or key
python -m deejay.cli --db deejay.db query --bpm-min 120 --bpm-max 128 --key Cmaj

# Update stored metadata
python -m deejay.cli --db deejay.db update <track_id> --bpm 126 --key Gmaj --cue-points '{"hotcue_1": 32}'

# Delete a track
python -m deejay.cli --db deejay.db delete <track_id>
```

The CLI honors the `DEEJAY_DB` environment variable for the database path when `--db` is omitted.
