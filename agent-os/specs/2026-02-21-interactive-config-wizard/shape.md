# Interactive Config Wizard — Shaping Notes

## Scope

Build an interactive CLI wizard that helps users create `~/.likedmusic/config.yml`. Styled like Claude Code's onboarding — polished, fun, colorful. Uses `rich` for display and `questionary` for interactive prompts.

## Decisions

- **Library choice:** `questionary` (simpler API, single dep) + `rich` (panels, tables, spinners)
- **Trigger:** Both dedicated `likedmusic config` subcommand AND auto-prompt on first `likedmusic sync` when no config exists
- **Wizard collects:** max download workers, playlists to sync (fetched from YTM), Apple Music playlist names
- **Backup dir NOT prompted:** stays at default; backup structure redesign is a separate plan
- **max_workers persisted in YAML:** CLI `--workers` flag overrides config value
- **Auth required first:** wizard checks for browser.json, runs setup if missing
- **Playlist fetch:** connects to YTM API, shows multi-select checkbox with library playlists
- **Non-TTY safety:** every questionary result checked for None (Ctrl+C / pipe), abort gracefully

## Context

- **Visuals:** Claude Code onboarding style as inspiration
- **References:** Existing `cli.py` setup subcommand, `playlist_config.py` load/save logic
- **Product alignment:** Personal tool, macOS-only — polished CLI fits the use case
