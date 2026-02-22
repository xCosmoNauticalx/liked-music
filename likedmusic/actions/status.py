"""View sync status action."""

from rich.console import Console
from rich.table import Table

from likedmusic.actions.base import register


console = Console()


def _handle(dry_run: bool) -> None:
    from likedmusic.config import CONFIG_PATH
    from likedmusic.playlist_config import load_config
    from likedmusic.state import load_playlist_state

    if not CONFIG_PATH.exists():
        console.print("[yellow]No configuration found. Run 'Configure playlists' first.[/yellow]")
        return

    playlists, backup_dir, max_workers = load_config()

    table = Table(title="Sync Status", show_header=True)
    table.add_column("Playlist", style="cyan")
    table.add_column("Apple Music", style="green")
    table.add_column("Songs Synced", justify="right")
    table.add_column("Last Sync", style="dim")

    for pl in playlists:
        state = load_playlist_state(backup_dir, pl.name)
        song_count = len(state.get("synced_songs", {}))
        last_sync = state.get("last_sync", "never")
        table.add_row(pl.name, pl.apple_music_playlist, str(song_count), last_sync)

    console.print(table)
    console.print(f"\nWorkers: [bold]{max_workers}[/bold]")
    console.print(f"Backup dir: [dim]{backup_dir}[/dim]")


register(
    name="View sync status",
    description="Show configured playlists and sync info",
    handler=_handle,
)
