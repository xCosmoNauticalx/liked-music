"""CLI entry point for LikedMusic."""

import argparse

from likedmusic.config import MAX_DOWNLOAD_WORKERS, ensure_dirs


def cmd_setup(args: argparse.Namespace) -> None:
    """Run browser auth setup flow."""
    from likedmusic.ytmusic import setup_ytmusic_browser

    ensure_dirs()
    setup_ytmusic_browser()


def cmd_sync(args: argparse.Namespace) -> None:
    """Run full sync pipeline."""
    from likedmusic.sync_engine import run_sync

    run_sync(max_workers=args.workers, dry_run=args.dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="likedmusic",
        description="Sync YouTube Music liked songs to Apple Music",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup subcommand
    setup_parser = subparsers.add_parser("setup", help="Set up browser auth headers")
    setup_parser.set_defaults(func=cmd_setup)

    # sync subcommand
    sync_parser = subparsers.add_parser("sync", help="Sync liked songs")
    sync_parser.add_argument(
        "--workers",
        type=int,
        default=MAX_DOWNLOAD_WORKERS,
        help=f"Number of download workers (default: {MAX_DOWNLOAD_WORKERS})",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview sync actions without downloading or modifying anything",
    )
    sync_parser.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
