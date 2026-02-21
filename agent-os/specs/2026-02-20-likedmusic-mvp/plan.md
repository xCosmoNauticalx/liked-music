# LikedMusic MVP — Implementation Plan

## Overview

Python CLI tool that syncs liked songs from YouTube Music → local M4A files → Apple Music playlist. One-directional sync, runs locally on macOS.

## Architecture

- **ytmusic.py** — OAuth setup + fetch liked songs via ytmusicapi
- **downloader.py** — Multi-threaded yt-dlp downloads to M4A
- **metadata.py** — Embed title/artist/album/art into M4A via mutagen
- **apple_music.py** — AppleScript wrappers for Music.app playlist management
- **state.py** — JSON sync state to avoid duplicates
- **sync_engine.py** — Orchestrates the full pipeline
- **cli.py** — argparse entry point (setup, sync subcommands)

## Sync Algorithm

1. Load sync state from `~/.likedmusic/sync_state.json`
2. Fetch liked songs from YTM (newest-first order)
3. Diff against synced set → determine new songs
4. Download new songs via yt-dlp (multi-threaded, retry with backoff)
5. Embed metadata (title, artist, album, album art) into each M4A
6. Copy to backup dir (`~/Music/LikedMusic-Backup/`) with `Artist - Title [videoId].m4a` naming
7. Add new songs to Apple Music playlist
8. Reorder playlist to match YTM order (in-place via AppleScript `move`)
9. Save updated state

## Key Decisions

- Video ID as filename for deduplication
- In-place reorder via `move` to avoid iCloud re-upload
- Failed downloads skip gracefully, don't halt batch
- Credentials via CLI args or env vars
