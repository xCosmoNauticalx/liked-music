# LikedMusic

Sync your YouTube Music playlists to Apple Music — interactively or via AI agent.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green)

LikedMusic keeps your YouTube Music playlists in sync with Apple Music. It downloads new tracks as M4A audio, embeds metadata, backs up files locally, and adds songs to Apple Music — all tracked with per-playlist state so re-runs only process what's new. It ships both an interactive CLI for personal use and an MCP server so AI agents can query status, preview changes, and trigger syncs programmatically without human interaction.

---

## Features

### Sync & Download
- Multi-playlist sync with per-playlist state tracking and crash recovery
- Parallel concurrent downloads via configurable thread pool (default: 4 workers)
- Metadata embedding — title, artist, album art — with robust remix/feat. parsing
- Backup system using human-readable `{Artist} - {Title}.m4a` filenames
- Dry-run mode to preview pending changes before committing

### Engineering & Integration
- **MCP server** — AI agents can query status, preview changes, and trigger syncs via standard protocol
- Browser-based auth with automatic cookie extraction (Chrome, Firefox, Safari via rookiepy)
- Atomic state writes (write to temp file → rename) with SHA-256 checksum integrity
- Apple Music integration via AppleScript automation (no Apple API key required)
- Real-time Rich progress dashboard during sync

---

## Tech Stack

| Component | Library / Tool |
|---|---|
| Language | Python 3.10+ |
| MCP server | FastMCP (mcp package) |
| YouTube Music API | ytmusicapi |
| Audio download | yt-dlp |
| Audio transcoding | FFmpeg |
| Metadata tagging | mutagen |
| Browser cookie auth | rookiepy |
| Terminal UI | Rich |
| Apple Music | AppleScript via osascript |

---

## Architecture

Two independent entry points share the same sync core:

```
┌──────────────┐    ┌──────────────────┐
│  likedmusic  │    │  likedmusic-mcp  │
│  (CLI)       │    │  (MCP server)    │
└──────┬───────┘    └────────┬─────────┘
       │                     │
       └──────────┬──────────┘
                  ▼
           SyncEngine
          ┌────┬────┬────┬──────┐
          │YTM │DL  │Meta│AppleM│
          └────┴────┴────┴──────┘
                  │
              State / Backup
```

`SyncEngine` is the only place where playlists are fetched, diffed, downloaded, and imported. Both the CLI and MCP server call into it, so behavior is identical regardless of how a sync is triggered.

---

## MCP Server

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is a standard that lets AI agents call tools in external processes. `likedmusic-mcp` exposes the sync engine as an MCP server over stdio, making it compatible with Claude Desktop, Cursor, and any other MCP-capable agent host.

### Tools exposed

| Tool | Description |
|---|---|
| `list_playlists` | List all configured playlists with synced/pending counts and last sync time |
| `get_playlist_status` | Detailed status for a single playlist |
| `get_sync_history` | Recent sync activity across all playlists, sorted by timestamp |
| `dry_run_sync` | Fetch tracks and compute diff without downloading or importing anything |
| `sync_playlist` | Full sync: download new tracks and import into Apple Music |
| `sync_playlist_download_only` | Download and tag new tracks without touching Apple Music |

### Add to Claude Desktop

```json
{
  "mcpServers": {
    "likedmusic": {
      "command": "likedmusic-mcp"
    }
  }
}
```

### Agent workflow example

An agent can autonomously:
1. Call `list_playlists` to see which playlists have pending tracks
2. Call `dry_run_sync` to inspect what would be downloaded
3. Call `sync_playlist` to execute the sync
4. Call `get_sync_history` to confirm the new tracks were added

No human interaction required at any step.

---

## Prerequisites & Installation

- macOS (Apple Music automation requires Music.app via osascript)
- Python 3.10+
- FFmpeg and ffprobe are bundled automatically via `static-ffmpeg`. If you already have both installed (e.g. `brew install ffmpeg`), the system versions take priority.

```bash
pip install -e .
```

This registers two executables: `likedmusic` (interactive CLI) and `likedmusic-mcp` (MCP server).

---

## Setup (one-time)

**1. Authenticate with YouTube Music**

```bash
likedmusic
```

Select "Set up YouTube Music auth". LikedMusic will extract cookies directly from your browser — no API key or OAuth flow needed. Supported browsers: Chrome, Firefox, Safari.

**2. Configure playlists**

```bash
likedmusic
```

Select "Configure playlists". The wizard prompts for playlist name, YouTube Music source (liked songs or a playlist URL), and the Apple Music playlist to sync into.

---

## Usage

### Interactive CLI

```bash
likedmusic
```

Menu-driven interface for syncing playlists, viewing status, reconfiguring, and running dry runs.

### MCP server

```bash
likedmusic-mcp
```

Starts the stdio MCP server. Wire it to any MCP-compatible agent host using the config snippet above.

---

## How It Works

A sync run proceeds in five steps:

1. **Fetch** — ytmusicapi retrieves the current track list from YouTube Music for each configured playlist.
2. **Diff** — the fetched list is compared against the per-playlist state file (`state.json`). Only tracks not in `synced_songs` are queued.
3. **Download** — yt-dlp downloads queued tracks in parallel using a thread pool. FFmpeg post-processes audio to M4A.
4. **Tag & back up** — mutagen embeds title, artist, and album art. Remix and featured-artist patterns in track titles are parsed and normalized. Files are copied to `~/Music/LikedMusic-Backup/Backup/` with human-readable names.
5. **Import & persist** — osascript adds each file to the configured Apple Music playlist. State is written atomically (temp file → rename) with a SHA-256 checksum to prevent partial-write corruption.

Crash recovery: if a run is interrupted mid-download, the next run picks up where it left off — state is only written after a track is fully imported.

---

## Data & File Layout

```
~/.likedmusic/
├── browser.json       # YouTube Music auth (browser cookies)
├── config.yml         # Playlist configuration
└── downloads/         # Temporary download cache (safe to delete)

~/Music/LikedMusic-Backup/
└── Backup/
    └── {Artist} - {Title}.m4a

~/Music/LikedMusic-Backup/{PlaylistName}/
└── state.json         # Per-playlist sync state with SHA-256 checksums
```
