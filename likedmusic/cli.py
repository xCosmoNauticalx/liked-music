"""CLI entry point for LikedMusic."""

import argparse

from likedmusic.config import CONFIG_PATH, ensure_dirs


def cmd_setup(args: argparse.Namespace) -> None:
    """Run browser auth setup flow."""
    from likedmusic.ytmusic import setup_ytmusic_browser

    ensure_dirs()
    setup_ytmusic_browser()


def cmd_config(args: argparse.Namespace) -> None:
    """Run interactive config wizard."""
    from likedmusic.config_wizard import run_wizard

    ensure_dirs()
    run_wizard()


def cmd_sync(args: argparse.Namespace) -> None:
    """Run full sync pipeline."""
    if not CONFIG_PATH.exists():
        import questionary

        if questionary.confirm("No config found. Run setup wizard?", default=True).ask():
            from likedmusic.config_wizard import run_wizard

            ensure_dirs()
            run_wizard()
            if not CONFIG_PATH.exists():
                return

    from likedmusic.sync_engine import run_sync

    run_sync(
        max_workers=args.workers,
        dry_run=args.dry_run,
        playlist_name=args.playlist,
        sync_all=args.sync_all,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="likedmusic",
        description="Sync YouTube Music liked songs to Apple Music",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup subcommand
    setup_parser = subparsers.add_parser("setup", help="Set up browser auth headers")
    setup_parser.set_defaults(func=cmd_setup)

    # config subcommand
    config_parser = subparsers.add_parser("config", help="Interactive config wizard")
    config_parser.set_defaults(func=cmd_config)

    # sync subcommand
    sync_parser = subparsers.add_parser("sync", help="Sync liked songs")
    sync_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of download workers (default: from config or 4)",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview sync actions without downloading or modifying anything",
    )
    playlist_group = sync_parser.add_mutually_exclusive_group()
    playlist_group.add_argument(
        "--all",
        action="store_true",
        dest="sync_all",
        help="Sync all configured playlists",
    )
    playlist_group.add_argument(
        "--playlist",
        type=str,
        default=None,
        help="Sync a specific playlist by name",
    )
    sync_parser.set_defaults(func=cmd_sync, sync_all=False)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
