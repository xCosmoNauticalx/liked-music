# Multi-Playlist Sync — Shaping Notes

## Scope

Expand LikedMusic from syncing only the liked songs playlist to supporting multiple configurable YouTube Music playlists, each syncing to a separate Apple Music playlist with backups organized into subfolders.

## Decisions

- YAML config file at `~/.likedmusic/config.yml` (optional — tool works without it)
- Top-level `backup_dir` in config; playlists auto-get subfolders by name
- Playlist names resolved to IDs via `get_library_playlists()`, cached in config after first lookup
- `synced_songs` stays global for cross-playlist dedup; `playlist_order` becomes per-playlist
- CLI: `sync` defaults to liked only, `--all` for all playlists, `--playlist "Name"` for specific
- Apple Music playlists auto-created with user confirmation prompt
- No `" & "` splitting of structured artist names (some artists have `&` in their name)

## Context

- **Visuals:** None
- **References:** Existing sync pipeline in `likedmusic/sync_engine.py`, state management in `likedmusic/state.py`
- **Product alignment:** Extends MVP to support multiple playlists (not in current roadmap but natural evolution)

## Standards Applied

- root/general — Keep code simple, don't over-engineer
- root/error-handling — Use EAFP pattern
- root/virtual-env — Source .venv before running or installing packages
