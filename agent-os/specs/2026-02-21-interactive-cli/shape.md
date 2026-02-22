# Interactive CLI — Shaping Notes

## Scope

Replace argparse subcommands with an interactive, wizard-driven CLI using a pluggable action registry. Similar to Claude Code's interactive style.

## Decisions

- Action menu loops until user selects Quit (not one-shot)
- Registry pattern: modules call `register()` at import time, menu built dynamically
- Only `--dry-run` flag kept; all other subcommands removed
- Handler contract: `(dry_run: bool) -> None`
- Auto-setup on first launch if no config exists

## Context

- **Visuals:** Claude Code CLI as inspiration
- **References:** `likedmusic/config_wizard.py` — existing interactive patterns with questionary
- **Product alignment:** Personal tool, simplicity over configurability
