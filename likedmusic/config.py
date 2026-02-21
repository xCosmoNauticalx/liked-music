"""Paths and constants for LikedMusic."""

from pathlib import Path

DATA_DIR = Path.home() / ".likedmusic"
BROWSER_AUTH_PATH = DATA_DIR / "browser.json"
STATE_PATH = DATA_DIR / "sync_state.json"
DOWNLOADS_DIR = DATA_DIR / "downloads"
BACKUP_DIR = Path.home() / "Music" / "LikedMusic-Backup"
PLAYLIST_NAME = "YTM Liked Songs"
MAX_DOWNLOAD_WORKERS = 4


def ensure_dirs():
    """Create runtime directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
