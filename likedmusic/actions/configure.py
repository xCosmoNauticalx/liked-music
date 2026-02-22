"""Configure playlists action."""

from likedmusic.actions.base import register


def _handle(dry_run: bool) -> None:
    from likedmusic.config_wizard import run_wizard
    run_wizard()


register(
    name="Configure playlists",
    description="Set up which playlists to sync",
    handler=_handle,
)
