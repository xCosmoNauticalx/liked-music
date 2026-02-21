"""CLI entry point for LikedMusic."""

import argparse
import os
import sys

from likedmusic.config import MAX_DOWNLOAD_WORKERS, ensure_dirs


def _get_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """Get client ID and secret from args or environment variables."""
    client_id = args.client_id or os.environ.get("LIKEDMUSIC_CLIENT_ID")
    client_secret = args.client_secret or os.environ.get("LIKEDMUSIC_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "Error: --client-id and --client-secret are required "
            "(or set LIKEDMUSIC_CLIENT_ID and LIKEDMUSIC_CLIENT_SECRET).",
            file=sys.stderr,
        )
        sys.exit(1)

    return client_id, client_secret


def cmd_setup(args: argparse.Namespace) -> None:
    """Run OAuth setup flow."""
    from likedmusic.ytmusic import setup_ytmusic_oauth

    ensure_dirs()
    client_id, client_secret = _get_credentials(args)
    setup_ytmusic_oauth(client_id, client_secret)


def cmd_sync(args: argparse.Namespace) -> None:
    """Run full sync pipeline."""
    from likedmusic.sync_engine import run_sync

    client_id, client_secret = _get_credentials(args)
    run_sync(client_id, client_secret, max_workers=args.workers, dry_run=args.dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="likedmusic",
        description="Sync YouTube Music liked songs to Apple Music",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup subcommand
    setup_parser = subparsers.add_parser("setup", help="Run OAuth setup flow")
    setup_parser.add_argument("--client-id", help="Google OAuth client ID")
    setup_parser.add_argument("--client-secret", help="Google OAuth client secret")
    setup_parser.set_defaults(func=cmd_setup)

    # sync subcommand
    sync_parser = subparsers.add_parser("sync", help="Sync liked songs")
    sync_parser.add_argument("--client-id", help="Google OAuth client ID")
    sync_parser.add_argument("--client-secret", help="Google OAuth client secret")
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
