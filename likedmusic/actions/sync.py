"""Sync playlists action."""

from datetime import datetime, timezone

import questionary
from rich.console import Console

from likedmusic.actions.base import register
from likedmusic.config_wizard import CHECKBOX_STYLE, prompt_max_workers
from likedmusic.playlist_config import load_config

console = Console()

_ADD_PENDING = "__add_pending__"
_SYNC_MODE_NORMAL = "Download + Apple Music"
_SYNC_MODE_DOWNLOAD_ONLY = "Download only (skip Apple Music)"


def _relative_time(iso_ts: str | None) -> str:
    """Return a human-readable relative time string like '3 days ago'."""
    if not iso_ts:
        return "never"
    try:
        dt = datetime.fromisoformat(iso_ts)
        delta = datetime.now(timezone.utc) - dt
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            return f"{hours}h ago" if hours else "just now"
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        return f"{months}mo ago"
    except (ValueError, TypeError):
        return iso_ts


def _fetch_all_stats(playlists, backup_dir):
    """Pre-fetch each playlist from YTM and compute new-song counts.

    Returns a list of dicts:
      {playlist, new_count, pending_count, last_sync, tracks}
    """
    from likedmusic import state as st, const
    from likedmusic.sync_engine import _fetch_tracks

    all_synced_ids = st.load_all_synced_ids(backup_dir)
    results = []

    for pl in playlists:
        with console.status(f"Checking '{pl.name}'..."):
            try:
                tracks = _fetch_tracks(pl, playlists, backup_dir)
            except Exception as e:
                console.print(f"[red]Failed to fetch '{pl.name}': {e}[/red]")
                tracks = []

        pl_state = st.load_playlist_state(backup_dir, pl.name)
        new_count = sum(
            1 for t in tracks
            if t.get(const.VIDEO_ID_KEY) and t[const.VIDEO_ID_KEY] not in all_synced_ids
        )
        pending_count = len(st.get_pending_songs(pl_state))
        last_sync = _relative_time(pl_state.get("last_sync"))

        results.append({
            "playlist": pl,
            "new_count": new_count,
            "pending_count": pending_count,
            "last_sync": last_sync,
            "tracks": tracks,
        })

    return results


def _build_choice_title(stat: dict) -> str:
    parts = []
    if stat["new_count"]:
        parts.append(f"{stat['new_count']} new")
    if stat["pending_count"]:
        parts.append(f"{stat['pending_count']} pending")
    suffix = ", ".join(parts) if parts else "up to date"
    return f"{stat['playlist'].name} — {suffix}  (last: {stat['last_sync']})"


def _handle(dry_run: bool) -> None:
    from likedmusic.sync_engine import run_sync, add_pending_to_apple_music

    playlists, backup_dir, _ = load_config()

    if not playlists:
        console.print("[yellow]No playlists configured. Run 'Configure playlists' first.[/yellow]")
        return

    stats = _fetch_all_stats(playlists, backup_dir)

    total_pending = sum(s["pending_count"] for s in stats)

    choices = []

    if total_pending:
        choices.append(questionary.Choice(
            title=f"Add {total_pending} pending song(s) to Apple Music",
            value=_ADD_PENDING,
        ))

    for stat in stats:
        choices.append(questionary.Choice(
            title=_build_choice_title(stat),
            value=stat["playlist"].name,
            checked=stat["new_count"] > 0 or stat["pending_count"] > 0,
        ))

    selected = questionary.checkbox(
        "Select playlists to sync (space to toggle, enter to confirm):",
        choices=choices,
        style=CHECKBOX_STYLE,
    ).ask()

    if selected is None:
        return

    if not selected:
        console.print("[dim]Nothing selected.[/dim]")
        return

    # Handle "add pending" selection
    add_pending_selected = _ADD_PENDING in selected
    playlist_names = [s for s in selected if s != _ADD_PENDING]

    if add_pending_selected:
        for stat in stats:
            if stat["pending_count"]:
                add_pending_to_apple_music(stat["playlist"], backup_dir)

    if not playlist_names:
        return

    # Ask workers count before starting sync
    max_workers_result = prompt_max_workers()
    if max_workers_result is None:
        return

    # Ask sync mode
    mode = questionary.select(
        "Sync mode:",
        choices=[_SYNC_MODE_NORMAL, _SYNC_MODE_DOWNLOAD_ONLY],
    ).ask()

    if mode is None:
        return

    download_only = mode == _SYNC_MODE_DOWNLOAD_ONLY

    for name in playlist_names:
        run_sync(
            max_workers=max_workers_result,
            dry_run=dry_run,
            playlist_name=name,
            download_only=download_only,
        )


register(
    name="Sync playlists",
    description="Sync YouTube Music playlists to Apple Music",
    handler=_handle,
)
