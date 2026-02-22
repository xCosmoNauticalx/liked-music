"""Interactive configuration wizard for LikedMusic."""

import sys

import questionary
from questionary import Style
from rich.console import Console
from rich.table import Table

from likedmusic import const

CHECKBOX_STYLE = Style([
    ("pointer", "fg:#00bfff bold"),
    ("highlighted", "fg:#00bfff"),
    ("selected", "fg:#cc5454"),
])
from likedmusic.config import BACKUP_DIR, BROWSER_AUTH_PATH, MAX_DOWNLOAD_WORKERS
from likedmusic.playlist_config import PlaylistConfig, save_config

console = Console()


def _abort() -> None:
    """Print cancellation message and exit."""
    console.print("\n[yellow]Setup cancelled.[/yellow]")
    sys.exit(1)


def _ask(result):
    """Check questionary result for None (Ctrl+C / non-TTY) and abort if so."""
    if result is None:
        _abort()
    return result


def _ensure_auth() -> bool:
    """Check for browser.json, run setup if missing. Return True if auth ready."""
    if BROWSER_AUTH_PATH.is_file():
        console.print("[green]✓[/green] YouTube Music auth found.")
        return True

    console.print("[yellow]![/yellow] YouTube Music auth not found.")
    run_setup = _ask(
        questionary.confirm("Run browser auth setup now?", default=True).ask()
    )
    if not run_setup:
        console.print("Auth is required to fetch your playlists.")
        return False

    from likedmusic.ytmusic import setup_ytmusic_browser

    setup_ytmusic_browser()

    if not BROWSER_AUTH_PATH.is_file():
        console.print("[red]Auth setup failed. Please try again.[/red]")
        return False

    console.print("[green]✓[/green] Auth setup complete.")
    return True


def _fetch_library_playlists() -> list[dict]:
    """Fetch user's YTM library playlists with a spinner."""
    from likedmusic.ytmusic import _get_ytm_client

    with console.status("Fetching your YouTube Music playlists..."):
        ytm = _get_ytm_client()
        library = ytm.get_library_playlists(limit=None)

    console.print(f"[green]✓[/green] Found {len(library)} playlist(s) in your library.")
    return library


def _prompt_max_workers() -> int:
    """Ask for max download workers with validation."""
    result = _ask(
        questionary.text(
            "Max download workers:",
            default=str(MAX_DOWNLOAD_WORKERS),
            validate=lambda val: val.isdigit() and 1 <= int(val) <= 16
            or "Enter a number between 1 and 16",
        ).ask()
    )
    return int(result)


def _prompt_playlist_selection(library_playlists: list[dict]) -> list[dict]:
    """Show multi-select checkbox of YTM library playlists."""
    playlist_choices = []
    for pl in library_playlists:
        title = pl.get("title", "?")
        playlist_choices.append(
            questionary.Choice(
                title=title,
                value={
                    "title": title,
                    "playlistId": pl.get("playlistId"),
                    "source": title,
                },
            )
        )

    selected = _ask(
        questionary.checkbox(
            "Select playlists to sync (space to toggle, enter to confirm):",
            choices=playlist_choices,
            style=CHECKBOX_STYLE,
            validate=lambda sel: len(sel) > 0 or "Select at least one playlist",
        ).ask()
    )
    return selected


def _prompt_apple_music_names(selected: list[dict]) -> list[PlaylistConfig]:
    """For each selected playlist, ask for the Apple Music playlist name."""
    playlists = []
    for item in selected:
        name = item["title"]
        source = item["source"]
        playlist_id = item.get("playlistId")

        apple_name = _ask(
            questionary.text(
                f'Apple Music playlist name for "{name}":',
                default=name,
            ).ask()
        )

        playlists.append(
            PlaylistConfig(
                name=name,
                source=source,
                playlist_id=playlist_id,
                apple_music_playlist=apple_name,
            )
        )
    return playlists


def _show_summary(playlists: list[PlaylistConfig], max_workers: int) -> bool:
    """Display a rich table summary and ask for confirmation."""
    console.print()

    table = Table(title="Playlists to Sync", show_header=True)
    table.add_column("YTM Source", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Apple Music Playlist", style="green")

    for pl in playlists:
        source_type = "liked" if pl.source == const.LIKED_PLAYLIST_KEY else "playlist"
        table.add_row(pl.name, source_type, pl.apple_music_playlist)

    console.print(table)
    console.print(f"\n  Workers: [bold]{max_workers}[/bold]")
    console.print()

    return _ask(questionary.confirm("Save this configuration?", default=True).ask())


def run_wizard() -> None:
    """Main entry point for the interactive config wizard."""
    if not _ensure_auth():
        return

    max_workers = _prompt_max_workers()

    try:
        library_playlists = _fetch_library_playlists()
    except Exception as e:
        console.print(f"[red]Failed to fetch playlists: {e}[/red]")
        console.print("Your auth may be expired. Select [bold]Set up YouTube Music auth[/bold] from the main menu.")
        return

    selected = _prompt_playlist_selection(library_playlists)
    playlists = _prompt_apple_music_names(selected)

    if not _show_summary(playlists, max_workers):
        console.print("[yellow]Setup cancelled.[/yellow]")
        return

    save_config(playlists, BACKUP_DIR, max_workers)

    from likedmusic.config import CONFIG_PATH

    console.print(f"\n[green]✓ Config saved to {CONFIG_PATH}[/green]")
    console.print("  Select [bold]Sync playlists[/bold] from the main menu to start syncing!")
