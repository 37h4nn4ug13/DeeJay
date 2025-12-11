import hashlib
import json
from dataclasses import dataclass
from typing import Dict


KEYS = [
    "Cmaj",
    "Gmaj",
    "Dmaj",
    "Amaj",
    "Emaj",
    "Bmaj",
    "F#maj",
    "C#maj",
    "Fmaj",
    "Bbmaj",
    "Ebmaj",
    "Abmaj",
    "Dbmaj",
    "Gbmaj",
    "Cbmaj",
]


@dataclass
class MetadataEstimate:
    bpm: float
    musical_key: str
    intro_start: float
    intro_end: float
    outro_start: float
    outro_end: float
    cue_points: str


def _hash_number(value: str) -> int:
    digest = hashlib.sha1(value.encode()).hexdigest()
    return int(digest[:8], 16)


def placeholder_from_file(file_path: str) -> MetadataEstimate:
    """Compute a deterministic placeholder for metadata from the file path."""
    seed = _hash_number(file_path)
    bpm = 80 + (seed % 81)  # 80-160 BPM range
    key = KEYS[seed % len(KEYS)]
    intro_start = 0.0
    intro_end = 15.0
    outro_end = 300.0
    outro_start = max(intro_end + 30.0, outro_end - 20.0)
    cue_points = json.dumps({"hotcue_1": intro_end, "hotcue_2": outro_start})
    return MetadataEstimate(
        bpm=float(bpm),
        musical_key=key,
        intro_start=intro_start,
        intro_end=intro_end,
        outro_start=outro_start,
        outro_end=outro_end,
        cue_points=cue_points,
    )


def as_dict(estimate: MetadataEstimate) -> Dict[str, float | str]:
    return {
        "bpm": estimate.bpm,
        "musical_key": estimate.musical_key,
        "intro_start": estimate.intro_start,
        "intro_end": estimate.intro_end,
        "outro_start": estimate.outro_start,
        "outro_end": estimate.outro_end,
        "cue_points": estimate.cue_points,
    }
