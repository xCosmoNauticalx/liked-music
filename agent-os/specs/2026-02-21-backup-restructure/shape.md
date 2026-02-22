# Backup Restructure — Shaping Notes

## Scope

Restructure backup and state management:
1. Replace single global `~/.likedmusic/sync_state.json` with per-playlist `.json` files in `backup_dir`
2. Flatten audio backups from per-playlist subdirs into single `Backup/` folder
3. Add SHA256 checksum + `.bak` file for corruption protection
4. Migrate existing state on first run

## Decisions

- Per-playlist .json files **replace** global state entirely (no coexistence)
- Single flat `Backup/` folder — dedup by video ID in filename
- Checksum: SHA256 of deterministic JSON payload (sort_keys=True)
- Recovery: copy current to `.bak` before writing; fall back to `.bak` if main file corrupt
- Cross-playlist dedup: scan all `.json` files to build global synced ID set

## Context

- **Visuals:** None
- **References:** `likedmusic/state.py`, `likedmusic/sync_engine.py`, `likedmusic/playlist_config.py`, `likedmusic/config_wizard.py`
- **Product alignment:** N/A

## Standards Applied

- general — Keep simple, don't over-engineer
- error-handling — EAFP pattern for file I/O
- virtual-env — Source .venv before commands
