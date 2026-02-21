# LikedMusic MVP — Shaping Notes

## Problem

No easy way to keep Apple Music in sync with YouTube Music liked songs. Manual process is tedious.

## Solution Shape

One-directional CLI sync: YTM → local M4A → Apple Music playlist.

## Boundaries

- **In scope:** Fetch liked songs, download as M4A, embed metadata, create/update Apple Music playlist, track sync state
- **Out of scope:** Two-way sync, Apple Music → YTM, GUI, scheduling/daemon mode, playlist deletion management

## Design Decisions

### Why M4A?
YouTube Music sources are AAC-encoded. M4A preserves quality without re-encoding. Apple Music natively supports M4A.

### Why video ID as filename?
Guarantees uniqueness. Multiple songs can share the same title. Makes deduplication trivial via filesystem check.

### Why in-place reorder instead of rebuild?
Rebuilding (delete all + re-add) triggers iCloud Music Library to re-upload all audio files. Moving tracks in-place should only sync playlist metadata.

### Why backup directory?
Apple Music library is opaque. If the library gets corrupted or reset, having a backup with human-readable filenames (`Artist - Title [videoId].m4a`) means no re-downloading.

### Why not store credentials in config?
OAuth tokens are stored in `~/.likedmusic/oauth.json` (managed by ytmusicapi). Client ID/secret are passed via CLI args or env vars — not persisted, following security best practices.

### Thread safety
Each download worker gets its own `YoutubeDL` instance. yt-dlp's `YoutubeDL` is not thread-safe when shared.

## Risks

- AppleScript playlist reorder may still trigger iCloud re-upload (will need testing)
- YouTube Music API rate limits on large libraries
- yt-dlp breakage due to YouTube changes (mitigated by retries + graceful skip)
