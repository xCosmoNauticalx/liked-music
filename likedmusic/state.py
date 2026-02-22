"""Sync state persistence using JSON."""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from likedmusic import config, const


def load_state() -> dict:
    """Load sync state from disk.
    
    Reads the state file from the configured STATE_PATH and parses it as JSON.
    If the file doesn't exist, returns a default empty state structure with
    initialized keys for synced songs, last sync timestamp, and playlist order.
    
    Returns:
        dict: A dictionary containing the sync state with the following keys:
            - synced_songs: Dictionary mapping video IDs to song metadata
            - last_sync: ISO format timestamp of the last sync, or None
            - playlist_order: List of video IDs representing playlist order
    """
    if config.STATE_PATH.exists():
        return json.loads(config.STATE_PATH.read_text())
    return {
        const.SYNCED_SONGS_KEY: {},
        const.LAST_SYNC_KEY: None,
        const.PLAYLIST_ORDER_KEY: [],
    }


def save_state(state: dict) -> None:
    """Atomically write state to disk using a temporary file and rename operation.
    
    This function persists the sync state to disk in a safe, atomic manner by first
    writing to a temporary file and then renaming it to the final destination. This
    approach ensures that the state file is never left in a partially written state.
    The function also updates the last_sync timestamp before saving.
    
    Args:
        state (dict): The state dictionary to persist. Should contain keys like
            synced_songs, playlist_order, and other sync-related data. The
            last_sync timestamp will be automatically updated to the current UTC time.
    
    Raises:
        Exception: Any exception that occurs during file writing or renaming is
            re-raised after attempting to clean up the temporary file.
    """
    state[const.LAST_SYNC_KEY] = datetime.now(timezone.utc).isoformat()
    config.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        dir=config.STATE_PATH.parent,
        suffix=".tmp",
    )
    tmp = Path(tmp_path)
    try:
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(config.STATE_PATH)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def get_synced_video_ids(state: dict) -> set[str]:
    """Extract the set of video IDs that have already been synced.
    
    This function retrieves all video IDs from the synced_songs dictionary in the
    state and returns them as a set. This is useful for quickly checking which
    songs have already been downloaded and processed during previous sync operations.
    
    Args:
        state (dict): The sync state dictionary containing synced song information.
            Expected to have a 'synced_songs' key with a dictionary mapping video
            IDs to their metadata. If the key is missing, an empty dictionary is
            assumed.
    
    Returns:
        set[str]: A set of video ID strings representing all songs that have been
            previously synced. Returns an empty set if no songs have been synced yet.
    """
    return set(state.get(const.SYNCED_SONGS_KEY, {}).keys())


def mark_synced(state: dict, video_id: str, title: str, artist: str, file_path: str) -> None:
    """Mark a song as synced in the state by recording its metadata.
    
    This function updates the sync state to record that a particular song has been
    successfully downloaded and processed. It stores the song's metadata including
    title, artist, file location, and the timestamp when it was synced. This information
    is used to track which songs have already been synced and avoid re-downloading them
    in subsequent sync operations.
    
    Args:
        state (dict): The sync state dictionary to update. This dictionary will be
            modified in-place to include the new synced song information.
        video_id (str): The unique YouTube Music video ID for the song. This serves
            as the key for storing and retrieving the song's sync information.
        title (str): The title of the song as retrieved from YouTube Music.
        artist (str): The artist name for the song as retrieved from YouTube Music.
        file_path (str): The local file system path where the downloaded song file
            is stored.
    
    Returns:
        None: This function modifies the state dictionary in-place and does not
            return a value.
    """
    state.setdefault(const.SYNCED_SONGS_KEY, {})[video_id] = {
        const.TITLE_KEY: title,
        const.ARTIST_KEY: artist,
        const.FILE_PATH_KEY: file_path,
        const.SYNCED_AT_KEY: datetime.now(timezone.utc).isoformat(),
    }


def get_playlist_order(state: dict, playlist_name: str) -> list[str]:
    """Get the stored order for a specific playlist.

    Falls back to top-level 'playlist_order' for backward compat with older
    state files that only tracked liked songs.
    """
    orders = state.get(const.PLAYLIST_ORDERS_KEY, {})
    if playlist_name in orders:
        return orders[playlist_name]
    if playlist_name == "YTM Liked Songs":
        return state.get(const.PLAYLIST_ORDER_KEY, [])
    return []


def update_playlist_order(state: dict, video_ids: list[str], playlist_name: str | None = None) -> None:
    """Store the current playlist order (list of video IDs).

    When playlist_name is given, stores in playlist_orders dict.
    Also updates top-level playlist_order for backward compat when
    playlist_name is None or "YTM Liked Songs".
    """
    if playlist_name:
        state.setdefault(const.PLAYLIST_ORDERS_KEY, {})[playlist_name] = video_ids
    if not playlist_name or playlist_name == "YTM Liked Songs":
        state[const.PLAYLIST_ORDER_KEY] = video_ids
