import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable

from .database import Database, Track
from .metadata import as_dict, placeholder_from_file

DEFAULT_DB_PATH = os.environ.get("DEEJAY_DB", os.path.join(os.getcwd(), "deejay.db"))


def _print_table(rows: Iterable[Dict[str, Any]]) -> None:
    for row in rows:
        print(json.dumps(row, indent=2))


def _track_to_dict(track: Track) -> Dict[str, Any]:
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "file_uuid": track.file_uuid,
        "file_path": track.file_path,
        "bpm": track.bpm,
        "musical_key": track.musical_key,
        "intro_start": track.intro_start,
        "intro_end": track.intro_end,
        "outro_start": track.outro_start,
        "outro_end": track.outro_end,
        "cue_points": track.cue_points,
        "created_at": track.created_at,
        "updated_at": track.updated_at,
        "analyzed_at": track.analyzed_at,
    }


def cmd_migrate(args: argparse.Namespace) -> None:
    db = Database(args.db)
    db.apply_migrations()
    print(f"Migrations applied to {args.db}")


def cmd_import(args: argparse.Namespace) -> None:
    db = Database(args.db)
    db.apply_migrations()
    for file_path in args.files:
        estimate = placeholder_from_file(file_path)
        track = db.create_track(
            title=args.title or os.path.basename(file_path),
            artist=args.artist or "Unknown",
            file_path=file_path,
            **as_dict(estimate),
        )
        print(json.dumps(_track_to_dict(track), indent=2))


def cmd_get(args: argparse.Namespace) -> None:
    db = Database(args.db)
    track = db.get_track(args.id)
    if not track:
        print(f"Track {args.id} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(_track_to_dict(track), indent=2))


def cmd_query(args: argparse.Namespace) -> None:
    db = Database(args.db)
    tracks = db.list_tracks(
        bpm_min=args.bpm_min,
        bpm_max=args.bpm_max,
        musical_key=args.key,
    )
    _print_table([_track_to_dict(track) for track in tracks])


def cmd_update(args: argparse.Namespace) -> None:
    db = Database(args.db)
    track = db.update_track_metadata(
        args.id,
        bpm=args.bpm,
        musical_key=args.key,
        intro_start=args.intro_start,
        intro_end=args.intro_end,
        outro_start=args.outro_start,
        outro_end=args.outro_end,
        cue_points=args.cue_points,
    )
    if not track:
        print(f"Track {args.id} not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(_track_to_dict(track), indent=2))


def cmd_delete(args: argparse.Namespace) -> None:
    db = Database(args.db)
    db.delete_track(args.id)
    print(f"Deleted track {args.id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DeeJay SQLite catalog")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate_p = subparsers.add_parser("migrate", help="Apply schema migrations")
    migrate_p.set_defaults(func=cmd_migrate)

    import_p = subparsers.add_parser("import", help="Import audio files with placeholder metadata")
    import_p.add_argument("files", nargs="+", help="File paths to import")
    import_p.add_argument("--title", help="Title to use for imported tracks")
    import_p.add_argument("--artist", help="Artist to use for imported tracks")
    import_p.set_defaults(func=cmd_import)

    get_p = subparsers.add_parser("get", help="Fetch a track by ID")
    get_p.add_argument("id", help="Track ID")
    get_p.set_defaults(func=cmd_get)

    query_p = subparsers.add_parser("query", help="Query tracks by BPM or key")
    query_p.add_argument("--bpm-min", type=float, help="Minimum BPM")
    query_p.add_argument("--bpm-max", type=float, help="Maximum BPM")
    query_p.add_argument("--key", help="Musical key")
    query_p.set_defaults(func=cmd_query)

    update_p = subparsers.add_parser("update", help="Update stored metadata")
    update_p.add_argument("id", help="Track ID")
    update_p.add_argument("--bpm", type=float)
    update_p.add_argument("--key")
    update_p.add_argument("--intro-start", type=float)
    update_p.add_argument("--intro-end", type=float)
    update_p.add_argument("--outro-start", type=float)
    update_p.add_argument("--outro-end", type=float)
    update_p.add_argument("--cue-points")
    update_p.set_defaults(func=cmd_update)

    delete_p = subparsers.add_parser("delete", help="Delete a track")
    delete_p.add_argument("id", help="Track ID")
    delete_p.set_defaults(func=cmd_delete)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
