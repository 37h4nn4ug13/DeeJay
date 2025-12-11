# DeeJay

Background audio analysis helpers that offload waveform, peak, and beat grid
calculations to background threads. Analysis outputs are cached on disk and
referenced from a lightweight SQLite database so that subsequent loads are fast
and do not block the audio thread.

## Usage

```python
from pathlib import Path
from deejay import AudioEngine

engine = AudioEngine()
future = engine.prime_track("track-001", Path("/path/to/audio.wav"))
result = future.result()  # when needed
print(result.waveform_path)
```

Artifacts are written to `cache/<track_id>/` and tracked in
`data/analysis.sqlite`. Use the cached outputs to avoid recomputing work across
sessions.
