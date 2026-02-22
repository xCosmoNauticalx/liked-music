# Sync UX Improvements — Shaping Notes

## Scope

Fix several UX issues in the interactive CLI and add download-only debugging mode.

## Decisions

- Quit sentinel: use `_QUIT = object()` instead of `value=None` to distinguish from Ctrl+C
- Pending = `apple_music_added=False` in state; backward compat: missing field → True
- Pre-fetch YTM after "Sync playlists" selected; pre-check playlists with new songs
- "Add pending" is within the sync action, not a separate main menu action
- Workers prompt removed from wizard, asked in sync action before starting
- Ctrl+C during sync saves partial state and exits cleanly

## Context

- **Visuals:** None
- **References:** `likedmusic/cli.py`, `likedmusic/actions/sync.py`, `likedmusic/sync_engine.py`, `likedmusic/state.py`, `likedmusic/config_wizard.py`
- **Product alignment:** Personal debugging tool; reliability and clear feedback matter
