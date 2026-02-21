"""Sync state persistence using JSON."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from likedmusic.config import STATE_PATH


def load_state() -> dict:
    """Load sync state from disk. Returns empty state if file doesn't exist."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "synced_songs": {},
        "last_sync": None,
        "playlist_order": [],
    }


def save_state(state: dict) -> None:
    """Atomically write state to disk (temp file + rename)."""
    state["last_sync"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        dir=STATE_PATH.parent,
        suffix=".tmp",
    )
    tmp = Path(tmp_path)
    try:
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(STATE_PATH)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def get_synced_video_ids(state: dict) -> set[str]:
    """Return set of already-synced video IDs."""
    return set(state.get("synced_songs", {}).keys())


def mark_synced(
    state: dict,
    video_id: str,
    title: str,
    artist: str,
    file_path: str,
) -> None:
    """Mark a song as synced in the state."""
    state.setdefault("synced_songs", {})[video_id] = {
        "title": title,
        "artist": artist,
        "file_path": file_path,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def update_playlist_order(state: dict, video_ids: list[str]) -> None:
    """Store the current playlist order (list of video IDs)."""
    state["playlist_order"] = video_ids
