"""Playlist configuration loading and saving via YAML."""

import yaml
import tempfile
from pathlib import Path
from dataclasses import dataclass

from likedmusic import config, const


SOURCE_KEY = "source"
PLAYLISTS_KEY = "playlists"
BACKUP_DIR_KEY = "backup_dir"
APPLE_MUSIC_PLAYLIST_KEY = "apple_music_playlist"
MAX_WORKERS_KEY = "max_workers"


@dataclass
class PlaylistConfig:
    name: str
    source: str
    playlist_id: str | None = None
    apple_music_playlist: str = ""


def get_default_config() -> tuple[list[PlaylistConfig], Path, int]:
    """Return default configuration matching the original hardcoded behavior."""
    playlist = PlaylistConfig(
        name=config.PLAYLIST_NAME,
        source=const.LIKED_PLAYLIST_KEY,
        apple_music_playlist=config.PLAYLIST_NAME,
    )
    return [playlist], config.BACKUP_DIR, config.MAX_DOWNLOAD_WORKERS


def load_config() -> tuple[list[PlaylistConfig], Path, int]:
    """Load playlist configuration from YAML file.

    Returns (playlists, backup_dir, max_workers). Falls back to defaults if
    the config file is missing or invalid.
    """
    try:
        raw = yaml.safe_load(config.CONFIG_PATH.read_text())
    except FileNotFoundError:
        return get_default_config()

    if not raw or PLAYLISTS_KEY not in raw:
        return get_default_config()

    backup_dir = Path(raw.get(BACKUP_DIR_KEY, str(config.BACKUP_DIR))).expanduser()
    max_workers = raw.get(MAX_WORKERS_KEY, config.MAX_DOWNLOAD_WORKERS)

    playlists = []
    for entry in raw[PLAYLISTS_KEY]:
        if not entry.get(const.NAME_KEY) or not entry.get(SOURCE_KEY):
            raise ValueError(
                f"Playlist config missing required fields (name, source): {entry}"
            )
        playlists.append(
            PlaylistConfig(
                name=entry[const.NAME_KEY],
                source=entry[SOURCE_KEY],
                playlist_id=entry.get(const.PLAYLIST_ID_KEY),
                apple_music_playlist=entry.get(APPLE_MUSIC_PLAYLIST_KEY, entry[const.NAME_KEY]),
            )
        )

    return playlists, backup_dir, max_workers


def save_config(
    playlists: list[PlaylistConfig],
    backup_dir: Path,
    max_workers: int = config.MAX_DOWNLOAD_WORKERS,
) -> None:
    """Save playlist configuration to YAML file using atomic write."""
    data = {
        BACKUP_DIR_KEY: str(backup_dir),
        MAX_WORKERS_KEY: max_workers,
        PLAYLISTS_KEY: [],
    }
    for pl in playlists:
        entry = {
            const.NAME_KEY: pl.name,
            SOURCE_KEY: pl.source,
            APPLE_MUSIC_PLAYLIST_KEY: pl.apple_music_playlist,
        }
        if pl.playlist_id:
            entry[const.PLAYLIST_ID_KEY] = pl.playlist_id
        data[PLAYLISTS_KEY].append(entry)

    config.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=config.CONFIG_PATH.parent, suffix=".tmp")
    tmp = Path(tmp_path)
    try:
        tmp.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        tmp.rename(config.CONFIG_PATH)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
