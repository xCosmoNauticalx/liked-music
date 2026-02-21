# LikedMusic

Sync your YouTube Music liked songs to Apple Music.

## Prerequisites

- macOS (uses Music.app via AppleScript)
- Python >= 3.10
- ffmpeg (`brew install ffmpeg`)
- Google OAuth client credentials (for YouTube Music API)

## Install

```bash
pip install -e .
```

## Setup

Run the OAuth flow to authorize access to your YouTube Music account:

```bash
likedmusic setup --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

This opens a browser for Google OAuth and saves credentials to `~/.likedmusic/oauth.json`.

## Sync

```bash
likedmusic sync --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

Options:
- `--workers N` — Number of parallel download threads (default: 4)

You can also set credentials via environment variables:

```bash
export LIKEDMUSIC_CLIENT_ID=your_client_id
export LIKEDMUSIC_CLIENT_SECRET=your_client_secret
likedmusic sync
```

## What it does

1. Fetches your liked songs from YouTube Music
2. Downloads new songs as M4A audio files
3. Embeds metadata (title, artist, album, album art)
4. Backs up files to `~/Music/LikedMusic-Backup/`
5. Creates/updates a "YTM Liked Songs" playlist in Apple Music
6. Tracks sync state to avoid re-downloading

## Data

Runtime data is stored in `~/.likedmusic/`:
- `oauth.json` — YouTube Music OAuth credentials
- `sync_state.json` — Sync state (tracks already synced)
- `downloads/` — Downloaded M4A files
