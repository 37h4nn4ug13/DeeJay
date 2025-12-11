"""Command line interface for recording the master mix and quick saving it."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .database import SoundStore
from .recorder import MasterMixRecorder, SupportedFormat


def _default_output_path(directory: Path, audio_format: SupportedFormat) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = audio_format.lower()
    return directory / f"master_mix_{stamp}.{extension}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record the master mix to disk and quick-save it.")
    parser.add_argument("duration", type=float, help="Duration of the recording in seconds")
    parser.add_argument(
        "--format",
        dest="audio_format",
        default="WAV",
        choices=["WAV", "FLAC"],
        help="Audio container to use for the recording",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("recordings"),
        help="Directory to place recorded files (default: ./recordings)",
    )
    parser.add_argument(
        "--db",
        dest="database",
        type=Path,
        default=Path("data/deejay.db"),
        help="Path to the SQLite database for quick saves (default: data/deejay.db)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Optional title for the recording; defaults to file name",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recorder = MasterMixRecorder()

    output_path = _default_output_path(args.output_dir, args.audio_format)
    recording = recorder.record(args.duration, output_path, audio_format=args.audio_format)

    store = SoundStore(args.database)
    record_id = store.insert_sound(recording, title=args.title)

    print(f"Saved recording #{record_id} to {recording.file_path}")


if __name__ == "__main__":
    main()
