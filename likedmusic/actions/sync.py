"""Sync playlists action."""

import questionary
from rich.console import Console

from likedmusic.actions.base import register
from likedmusic.playlist_config import load_config

console = Console()


def _handle(dry_run: bool) -> None:
    playlists, _, _ = load_config()

    if len(playlists) == 1:
        from likedmusic.sync_engine import run_sync
        run_sync(dry_run=dry_run, sync_all=True)
        return

    choices = [
        questionary.Choice(title="Sync all playlists", value="all"),
    ]
    for pl in playlists:
        choices.append(questionary.Choice(title=pl.name, value=pl.name))

    selected = questionary.select(
        "Which playlist(s) to sync?",
        choices=choices,
    ).ask()

    if selected is None:
        return

    from likedmusic.sync_engine import run_sync

    if selected == "all":
        run_sync(dry_run=dry_run, sync_all=True)
    else:
        run_sync(dry_run=dry_run, playlist_name=selected)


register(
    name="Sync playlists",
    description="Sync YouTube Music playlists to Apple Music",
    handler=_handle,
)
