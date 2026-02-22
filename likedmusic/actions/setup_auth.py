"""Set up YouTube Music auth action."""

from rich.console import Console

from likedmusic.actions.base import register
from likedmusic.config import ensure_dirs

console = Console()


def _handle(dry_run: bool) -> None:
    from likedmusic.ytmusic import setup_ytmusic_browser

    ensure_dirs()
    try:
        setup_ytmusic_browser()
        console.print("[green]Auth setup complete.[/green]")
    except Exception as e:
        console.print(f"[red]Auth setup failed: {e}[/red]")


register(
    name="Set up YouTube Music auth",
    description="Refresh or set up browser authentication",
    handler=_handle,
)
