# Interactive CLI with Pluggable Action Registry

Replace argparse subcommands with a Claude Code-style interactive menu.
Running `likedmusic` launches an action menu; `--dry-run` is the only flag.

## Architecture

- Action registry: `Action` dataclass + `register()`/`get_actions()` in `likedmusic/actions/base.py`
- Each action is a module in `likedmusic/actions/` that calls `register()` at import time
- `likedmusic/actions/__init__.py` imports all action modules
- `likedmusic/cli.py` builds menu from `get_actions()`, loops with `questionary.select`

## Actions

1. **Sync playlists** — Prompts sync all / specific, delegates to `run_sync()`
2. **Configure playlists** — Calls `run_wizard()`
3. **Set up YouTube Music auth** — Calls `setup_ytmusic_browser()`
4. **View sync status** — Shows rich table of configured playlists and sync state

## Behavior

- Auto-runs config wizard on first launch if no config exists
- `--dry-run` flag passed to all action handlers
- KeyboardInterrupt during action returns to menu
- "Quit" option exits cleanly
