"""Per-playlist sync state persistence with checksum integrity."""

import hashlib
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from likedmusic import const

logger = logging.getLogger(__name__)


def _sanitize_state_filename(playlist_name: str) -> str:
    """Convert a playlist name to a safe filename (no extension)."""
    return re.sub(r'[<>:"/\\|?*\s]+', "_", playlist_name).strip("_")


def _state_path(backup_dir: Path, playlist_name: str) -> Path:
    """Return path to a playlist's state file."""
    return backup_dir / f"{_sanitize_state_filename(playlist_name)}.json"


def _compute_checksum(payload: dict) -> str:
    """SHA256 of deterministic JSON serialization."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _verify_checksum(data: dict) -> bool:
    """Verify the checksum field matches the rest of the data."""
    stored = data.get(const.CHECKSUM_KEY)
    if not stored:
        return False
    payload = {k: v for k, v in data.items() if k != const.CHECKSUM_KEY}
    return _compute_checksum(payload) == stored


def _default_playlist_state(playlist_name: str) -> dict:
    """Return an empty default state for a playlist."""
    return {
        const.PLAYLIST_NAME_KEY: playlist_name,
        const.LAST_SYNC_KEY: None,
        const.PLAYLIST_ORDER_KEY: [],
        const.SYNCED_SONGS_KEY: {},
    }


def load_playlist_state(backup_dir: Path, playlist_name: str) -> dict:
    """Load per-playlist state. Falls back to .bak if main file is corrupt."""
    path = _state_path(backup_dir, playlist_name)

    for candidate in [path, path.with_suffix(".json.bak")]:
        try:
            data = json.loads(candidate.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if _verify_checksum(data):
            payload = {k: v for k, v in data.items() if k != const.CHECKSUM_KEY}
            return payload
        logger.warning("Checksum mismatch in %s, trying backup", candidate)

    return _default_playlist_state(playlist_name)


def save_playlist_state(backup_dir: Path, playlist_name: str, playlist_state: dict) -> None:
    """Atomic-write playlist state with checksum. Copies current file to .bak first."""
    path = _state_path(backup_dir, playlist_name)
    backup_dir.mkdir(parents=True, exist_ok=True)

    playlist_state[const.LAST_SYNC_KEY] = datetime.now(timezone.utc).isoformat()
    playlist_state[const.PLAYLIST_NAME_KEY] = playlist_name

    checksum = _compute_checksum(playlist_state)
    data_with_checksum = {const.CHECKSUM_KEY: checksum, **playlist_state}

    # Copy current to .bak before overwriting
    if path.exists():
        shutil.copy2(path, path.with_suffix(".json.bak"))

    _, tmp_path = tempfile.mkstemp(dir=backup_dir, suffix=".tmp")
    tmp = Path(tmp_path)
    try:
        tmp.write_text(json.dumps(data_with_checksum, indent=2))
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def load_all_synced_ids(backup_dir: Path) -> set[str]:
    """Scan all playlist .json files and return union of synced video IDs."""
    ids: set[str] = set()
    try:
        json_files = list(backup_dir.glob("*.json"))
    except FileNotFoundError:
        return ids

    for path in json_files:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not _verify_checksum(data):
            logger.warning("Skipping %s: checksum mismatch", path.name)
            continue
        ids.update(data.get(const.SYNCED_SONGS_KEY, {}).keys())

    return ids


def load_all_synced_songs(backup_dir: Path) -> dict[str, dict]:
    """Scan all playlist .json files and merge synced_songs dicts."""
    merged: dict[str, dict] = {}
    try:
        json_files = list(backup_dir.glob("*.json"))
    except FileNotFoundError:
        return merged

    for path in json_files:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not _verify_checksum(data):
            continue
        merged.update(data.get(const.SYNCED_SONGS_KEY, {}))

    return merged


def load_all_pending_songs(backup_dir: Path) -> dict[str, dict]:
    """Scan all playlist .json files and return songs not yet added to Apple Music."""
    merged: dict[str, dict] = {}
    try:
        json_files = list(backup_dir.glob("*.json"))
    except FileNotFoundError:
        return merged

    for path in json_files:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not _verify_checksum(data):
            continue
        for vid, info in data.get(const.SYNCED_SONGS_KEY, {}).items():
            if not info.get("apple_music_added", True):
                merged[vid] = info

    return merged


# --- Pure dict helpers (work on a single playlist state dict) ---


def get_synced_video_ids(state: dict) -> set[str]:
    """Extract synced video IDs from a playlist state dict."""
    return set(state.get(const.SYNCED_SONGS_KEY, {}).keys())


def mark_synced(
    state: dict,
    video_id: str,
    title: str,
    artist: str,
    file_path: str,
    apple_music_added: bool = True,
) -> None:
    """Record a song as synced in the playlist state dict."""
    state.setdefault(const.SYNCED_SONGS_KEY, {})[video_id] = {
        const.TITLE_KEY: title,
        const.ARTIST_KEY: artist,
        const.FILE_PATH_KEY: file_path,
        const.SYNCED_AT_KEY: datetime.now(timezone.utc).isoformat(),
        "apple_music_added": apple_music_added,
    }


def get_pending_songs(state: dict) -> dict[str, dict]:
    """Return songs downloaded but not yet added to Apple Music.

    Missing apple_music_added field means it was added before this feature existed → treat as True.
    """
    return {
        vid: info
        for vid, info in state.get(const.SYNCED_SONGS_KEY, {}).items()
        if not info.get("apple_music_added", True)
    }


def mark_apple_music_added(state: dict, video_id: str) -> None:
    """Mark a downloaded song as added to Apple Music."""
    state[const.SYNCED_SONGS_KEY][video_id]["apple_music_added"] = True


def get_playlist_order(state: dict) -> list[str]:
    """Get the stored playlist order from a per-playlist state dict."""
    return state.get(const.PLAYLIST_ORDER_KEY, [])


def update_playlist_order(state: dict, video_ids: list[str]) -> None:
    """Set the playlist order in a per-playlist state dict."""
    state[const.PLAYLIST_ORDER_KEY] = video_ids


# --- Migration ---


def migrate_global_state(legacy_path: Path, backup_dir: Path, playlists: list) -> None:
    """Migrate legacy global sync_state.json to per-playlist .json files.

    Splits the global state into per-playlist state files based on playlist_orders.
    Songs not assigned to any playlist go into the first playlist's state.
    Renames the legacy file to .migrated after successful migration.
    """
    try:
        global_state = json.loads(legacy_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    all_synced = global_state.get(const.SYNCED_SONGS_KEY, {})
    playlist_orders = global_state.get("playlist_orders", {})
    top_level_order = global_state.get(const.PLAYLIST_ORDER_KEY, [])

    assigned_ids: set[str] = set()

    for pl in playlists:
        order = playlist_orders.get(pl.name, [])
        if not order and pl.name == "YTM Liked Songs":
            order = top_level_order

        songs_for_playlist = {
            vid: all_synced[vid]
            for vid in order
            if vid in all_synced
        }
        assigned_ids.update(songs_for_playlist.keys())

        pl_state = {
            const.PLAYLIST_NAME_KEY: pl.name,
            const.LAST_SYNC_KEY: global_state.get(const.LAST_SYNC_KEY),
            const.PLAYLIST_ORDER_KEY: order,
            const.SYNCED_SONGS_KEY: songs_for_playlist,
        }
        save_playlist_state(backup_dir, pl.name, pl_state)

    # Assign remaining songs to the first playlist
    unassigned = {vid: all_synced[vid] for vid in all_synced if vid not in assigned_ids}
    if unassigned and playlists:
        first_state = load_playlist_state(backup_dir, playlists[0].name)
        first_state.setdefault(const.SYNCED_SONGS_KEY, {}).update(unassigned)
        save_playlist_state(backup_dir, playlists[0].name, first_state)

    legacy_path.rename(legacy_path.with_suffix(".json.migrated"))
    print(f"Migrated legacy state to per-playlist files in {backup_dir}")
