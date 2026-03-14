"""MCP server exposing LikedMusic as agent-driven tools over stdio."""

import asyncio
import io
import sys
from contextlib import contextmanager

from mcp.server.fastmcp import FastMCP

from likedmusic import const, state
from likedmusic.config import BROWSER_AUTH_PATH, CONFIG_PATH
from likedmusic.playlist_config import load_config

mcp = FastMCP("likedmusic")


def _validate_prerequisites() -> None:
    """Raise if required config files are missing."""
    if not BROWSER_AUTH_PATH.is_file():
        raise FileNotFoundError(
            "browser.json not found. Run 'likedmusic setup' first to configure YouTube Music authentication."
        )
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            "config.yml not found. Run 'likedmusic config' first to configure playlists."
        )


@contextmanager
def _redirect_stdout():
    """Capture stdout to prevent print() from corrupting the stdio MCP protocol."""
    old = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        yield buf
    finally:
        sys.stdout = old


# --- Sync helpers (run in thread via asyncio.to_thread) ---


def _list_playlists_sync() -> dict:
    _validate_prerequisites()
    playlists, backup_dir, _ = load_config()
    result = []
    for pl in playlists:
        pl_state = state.load_playlist_state(backup_dir, pl.name)
        synced_count = len(pl_state.get(const.SYNCED_SONGS_KEY, {}))
        pending_count = len(state.get_pending_songs(pl_state))
        result.append({
            "name": pl.name,
            "source": pl.source,
            "apple_music_playlist": pl.apple_music_playlist,
            "synced_count": synced_count,
            "pending_count": pending_count,
            "last_sync": pl_state.get(const.LAST_SYNC_KEY),
        })
    return {"playlists": result}


def _get_playlist_status_sync(playlist_name: str) -> dict:
    _validate_prerequisites()
    playlists, backup_dir, _ = load_config()

    target = None
    for pl in playlists:
        if pl.name == playlist_name:
            target = pl
            break
    if not target:
        available = [p.name for p in playlists]
        raise ValueError(f"Playlist '{playlist_name}' not found. Available: {available}")

    pl_state = state.load_playlist_state(backup_dir, target.name)
    synced_songs = pl_state.get(const.SYNCED_SONGS_KEY, {})
    pending = state.get_pending_songs(pl_state)
    order = state.get_playlist_order(pl_state)

    return {
        "name": target.name,
        "source": target.source,
        "apple_music_playlist": target.apple_music_playlist,
        "synced_count": len(synced_songs),
        "pending_count": len(pending),
        "track_order_count": len(order),
        "last_sync": pl_state.get(const.LAST_SYNC_KEY),
    }


def _get_sync_history_sync(limit: int = 20) -> dict:
    _validate_prerequisites()
    playlists, backup_dir, _ = load_config()

    all_songs = []
    for pl in playlists:
        pl_state = state.load_playlist_state(backup_dir, pl.name)
        for vid, info in pl_state.get(const.SYNCED_SONGS_KEY, {}).items():
            all_songs.append({
                "video_id": vid,
                "title": info.get(const.TITLE_KEY, ""),
                "artist": info.get(const.ARTIST_KEY, ""),
                "synced_at": info.get(const.SYNCED_AT_KEY, ""),
                "playlist": pl.name,
                "apple_music_added": info.get("apple_music_added", True),
            })

    all_songs.sort(key=lambda s: s.get("synced_at", ""), reverse=True)
    return {"history": all_songs[:limit], "total_synced": len(all_songs)}


def _dry_run_sync_sync(playlist_name: str | None = None) -> dict:
    _validate_prerequisites()
    from likedmusic.sync_engine import run_sync

    with _redirect_stdout() as buf:
        run_sync(
            dry_run=True,
            playlist_name=playlist_name,
            sync_all=playlist_name is None,
            headless=True,
        )
        log = buf.getvalue()

    return {"status": "dry_run_complete", "log": log}


def _sync_playlist_sync(playlist_name: str | None = None) -> dict:
    _validate_prerequisites()
    from likedmusic.sync_engine import run_sync

    with _redirect_stdout() as buf:
        run_sync(
            playlist_name=playlist_name,
            sync_all=playlist_name is None,
            headless=True,
        )
        log = buf.getvalue()

    return {"status": "success", "log": log}


def _sync_playlist_download_only_sync(playlist_name: str | None = None) -> dict:
    _validate_prerequisites()
    from likedmusic.sync_engine import run_sync

    with _redirect_stdout() as buf:
        run_sync(
            playlist_name=playlist_name,
            sync_all=playlist_name is None,
            download_only=True,
            headless=True,
        )
        log = buf.getvalue()

    return {"status": "success", "log": log}


# --- MCP Tool definitions ---


@mcp.tool()
async def list_playlists() -> dict:
    """List all configured playlists with their sync status.

    Returns playlist names, sources, synced song counts, pending counts, and last sync timestamps.
    """
    return await asyncio.to_thread(_list_playlists_sync)


@mcp.tool()
async def get_playlist_status(playlist_name: str) -> dict:
    """Get detailed sync status for a specific playlist.

    Args:
        playlist_name: Name of the playlist as configured in config.yml.
    """
    return await asyncio.to_thread(_get_playlist_status_sync, playlist_name)


@mcp.tool()
async def get_sync_history(limit: int = 20) -> dict:
    """Get recent sync activity across all playlists.

    Args:
        limit: Maximum number of recent entries to return (default 20).
    """
    return await asyncio.to_thread(_get_sync_history_sync, limit)


@mcp.tool()
async def dry_run_sync(playlist_name: str | None = None) -> dict:
    """Preview what a sync would do without making any changes.

    Fetches tracks from YouTube Music and computes the diff, but does not download or import anything.

    Args:
        playlist_name: Sync a specific playlist. If omitted, previews all playlists.
    """
    return await asyncio.to_thread(_dry_run_sync_sync, playlist_name)


@mcp.tool()
async def sync_playlist(playlist_name: str | None = None) -> dict:
    """Trigger a full sync: download new songs and import them into Apple Music.

    This may take several minutes for large playlists.

    Args:
        playlist_name: Sync a specific playlist. If omitted, syncs all playlists.
    """
    return await asyncio.to_thread(_sync_playlist_sync, playlist_name)


@mcp.tool()
async def sync_playlist_download_only(playlist_name: str | None = None) -> dict:
    """Download new songs without importing them into Apple Music.

    Songs are downloaded, tagged with metadata, and backed up, but not added to any Apple Music playlist.

    Args:
        playlist_name: Sync a specific playlist. If omitted, syncs all playlists.
    """
    return await asyncio.to_thread(_sync_playlist_download_only_sync, playlist_name)


def main():
    """Entry point for the likedmusic-mcp command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
