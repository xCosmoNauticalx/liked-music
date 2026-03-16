"""CLI entry point for LikedMusic."""

import argparse

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel

from likedmusic.actions.base import get_actions
from likedmusic.config import CONFIG_PATH, ensure_dirs

console = Console()

BANNER = r"""
  _     _ _            _   __  __           _
 | |   (_) | _____  __| | |  \/  |_   _ ___(_) ___
 | |   | | |/ / _ \/ _` | | |\/| | | | / __| |/ __|
 | |___| |   <  __/ (_| | | |  | | |_| \__ \ | (__
 |_____|_|_|\_\___|\__,_| |_|  |_|\__,_|___/_|\___|
"""

# Sentinel — distinguishes "user chose Quit" from Ctrl+C/ESC (both return None from ask())
_QUIT = object()

MENU_STYLE = Style([
    ("pointer",     "fg:#00bfff bold"),
    ("highlighted", "fg:#00bfff"),
    ("selected",    "bg:#00bfff fg:white bold"),
    ("answer",      "fg:#00bfff bold"),
])


def _parse_args() -> bool:
    """Parse CLI args. Returns dry_run flag."""
    parser = argparse.ArgumentParser(
        prog="likedmusic",
        description="Sync YouTube Music playlists to Apple Music",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all actions without making changes",
    )
    args = parser.parse_args()
    return args.dry_run


def _auto_setup() -> None:
    """If no config exists, run the config wizard automatically."""
    if CONFIG_PATH.exists():
        return

    console.print("[yellow]No configuration found. Starting setup wizard...[/yellow]\n")
    from likedmusic.config_wizard import run_wizard

    run_wizard()

    if not CONFIG_PATH.exists():
        console.print("[dim]Setup incomplete. You can configure playlists from the menu.[/dim]\n")


def main() -> None:
    from likedmusic.logging_config import setup_logging
    setup_logging()
    dry_run = _parse_args()
    ensure_dirs()

    import likedmusic.actions  # noqa: F401 — triggers action registration

    console.print(Panel(BANNER, style="bold cyan", subtitle="LikedMusic"))

    if dry_run:
        console.print("[yellow]DRY-RUN MODE — no changes will be made[/yellow]\n")

    _auto_setup()

    actions = get_actions()

    while True:
        choices = [
            questionary.Choice(title=f"{a.name} — {a.description}", value=a)
            for a in actions
        ]
        choices.append(questionary.Choice(title="Quit", value=_QUIT))

        selected = questionary.select(
            "What would you like to do?",
            choices=choices,
            style=MENU_STYLE,
        ).ask()

        # None = Ctrl+C or ESC; _QUIT = user selected Quit
        if selected is None or selected is _QUIT:
            break

        try:
            selected.handler(dry_run)
        except KeyboardInterrupt:
            console.print("\n[yellow]Action cancelled.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")

        console.print()

    console.print("Goodbye!")


if __name__ == "__main__":
    main()
