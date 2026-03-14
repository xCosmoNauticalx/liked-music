"""Sync orchestration — coordinates fetching, downloading, and playlist management."""

import re
import shutil
from typing import List
from pathlib import Path

from likedmusic import apple_music, downloader, metadata, state, ytmusic, const
from likedmusic.config import AUDIO_BACKUP_SUBDIR, DOWNLOADS_DIR, LEGACY_STATE_PATH, ensure_dirs
from likedmusic.playlist_config import PlaylistConfig, load_config, save_config


def _sanitize_filename(s: str) -> str:
    """Replace characters invalid in filenames with underscores."""
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def _backup_file(file_path: Path, title: str, artist: str, video_id: str, audio_backup_dir: Path) -> None:
    """Copy an M4A file to the flat Backup/ directory with a human-readable name."""
    audio_backup_dir.mkdir(parents=True, exist_ok=True)
    safe_artist = _sanitize_filename(artist) if artist else "Unknown"
    safe_title = _sanitize_filename(title)
    backup_name = f"{safe_artist} - {safe_title} [{video_id}].m4a"
    dest = audio_backup_dir / backup_name
    if not dest.exists():
        shutil.copy2(file_path, dest)


def _fetch_tracks(playlist_cfg: PlaylistConfig, all_playlists, backup_dir):
    """Fetch tracks from YouTube Music for a playlist config."""
    if playlist_cfg.source == const.LIKED_PLAYLIST_KEY:
        print("Fetching liked songs from YouTube Music...")
        return ytmusic.fetch_liked_songs()

    if not playlist_cfg.playlist_id:
        print(f"Resolving playlist ID for '{playlist_cfg.source}'...")
        playlist_cfg.playlist_id = ytmusic.resolve_playlist_id(playlist_cfg.source)
        save_config(all_playlists, backup_dir)
        print(f"Cached playlist ID: {playlist_cfg.playlist_id}")

    print(f"Fetching tracks from '{playlist_cfg.source}'...")
    return ytmusic.fetch_playlist_songs(playlist_cfg.playlist_id)


def _dryrun_new_songs(playlist_name: str, order_changed: bool, new_songs: list[dict] = None) -> None:
    """Print what a sync would do without making changes."""
    if new_songs:
        print(f"[DRY RUN] Would download {len(new_songs)} new song(s):")
        for song in new_songs:
            title, artist = metadata.parse_title_artist(
                song.get(const.TITLE_KEY, ""),
                song.get(const.ARTISTS_KEY),
            )
            vid = song[const.VIDEO_ID_KEY]
            print(f"[DRY RUN]   Would download: {artist} - {title} ({vid})")
        print(
            f'[DRY RUN] Would add {len(new_songs)} track(s) to Apple Music playlist "{playlist_name}"'
        )
    else:
        print("[DRY RUN] No new songs to download.")
    if order_changed:
        print("[DRY RUN] Playlist order would change")


def _reorder_songs(playlist_name: str, all_synced_songs: dict, current_order: List[str]) -> None:
    """Reorder Apple Music playlist to match YouTube Music order."""
    print("\nPlaylist order changed, reordering...")
    ordered_names = []
    for video_id in current_order:
        song_info = all_synced_songs.get(video_id)
        if song_info:
            ordered_names.append(song_info[const.TITLE_KEY])
    if ordered_names:
        apple_music.reorder_playlist(playlist_name, ordered_names)
        print("Playlist reordered.")


def _download_new_songs(
    new_songs: List[dict],
    playlist_state: dict,
    max_workers: int,
    audio_backup_dir: Path,
    apple_music_added: bool = True,
) -> dict[str, Path]:
    """Download new songs, embed metadata, create backups, update playlist state."""
    from likedmusic.dashboard import DownloadDashboard

    print(f"\nDownloading {len(new_songs)} new song(s)...")
    with DownloadDashboard(total=len(new_songs)) as dashboard:
        downloaded = downloader.download_songs(new_songs, DOWNLOADS_DIR, max_workers, dashboard=dashboard)

    for song in new_songs:
        video_id = song[const.VIDEO_ID_KEY]
        if video_id not in downloaded:
            continue

        file_path = downloaded[video_id]
        title, artist = metadata.parse_title_artist(
            song.get(const.TITLE_KEY, ""),
            song.get(const.ARTISTS_KEY),
        )
        album_info = song.get("album")
        album = album_info.get(const.NAME_KEY) if album_info and isinstance(album_info, dict) else None
        thumbnail_url = metadata.get_best_thumbnail_url(song.get("thumbnails"))

        print(f"  Tagging: {artist} - {title}")
        metadata.embed_metadata(file_path, title, artist, album, thumbnail_url)
        _backup_file(file_path, title, artist, video_id, audio_backup_dir)
        state.mark_synced(playlist_state, video_id, title, artist, str(file_path), apple_music_added=apple_music_added)

    print(f"\n{len(downloaded)} song(s) downloaded and tagged.")
    return downloaded


def sync_playlist(
    playlist_cfg: PlaylistConfig,
    backup_dir: Path,
    all_playlists: list[PlaylistConfig],
    max_workers: int,
    dry_run: bool,
    download_only: bool = False,
    headless: bool = False,
) -> None:
    """Synchronize a single playlist from YouTube Music to Apple Music."""
    # Load this playlist's state and cross-playlist data
    playlist_state = state.load_playlist_state(backup_dir, playlist_cfg.name)
    all_synced_ids = state.load_all_synced_ids(backup_dir)
    all_synced_songs = state.load_all_synced_songs(backup_dir)

    tracks = _fetch_tracks(playlist_cfg, all_playlists, backup_dir)

    if not tracks:
        print("No tracks found.")
        return

    new_songs = [
        track for track in tracks
        if track.get(const.VIDEO_ID_KEY) and track[const.VIDEO_ID_KEY] not in all_synced_ids
    ]
    current_order = [track[const.VIDEO_ID_KEY] for track in tracks if track.get(const.VIDEO_ID_KEY)]
    previous_order = state.get_playlist_order(playlist_state)
    order_changed = current_order != previous_order

    # Songs already downloaded (by another playlist) that need adding to this playlist
    already_downloaded = {
        vid: all_synced_songs[vid][const.FILE_PATH_KEY]
        for vid in current_order
        if vid in all_synced_ids and vid not in {track[const.VIDEO_ID_KEY] for track in new_songs}
    }

    playlist_name = playlist_cfg.apple_music_playlist

    if dry_run:
        _dryrun_new_songs(playlist_name, order_changed, new_songs)
        return

    if not new_songs and not order_changed:
        print("Already up to date.")
        return

    audio_backup_dir = backup_dir / AUDIO_BACKUP_SUBDIR
    downloaded = {}

    try:
        if new_songs:
            downloaded = _download_new_songs(
                new_songs, playlist_state, max_workers, audio_backup_dir,
                apple_music_added=not download_only,
            )

        # Save playlist state after downloads
        state.save_playlist_state(backup_dir, playlist_cfg.name, playlist_state)

        if download_only:
            print(f"\n[DL ONLY] Downloaded {len(downloaded)} song(s). Not added to Apple Music.")
            state.update_playlist_order(playlist_state, current_order)
            state.save_playlist_state(backup_dir, playlist_cfg.name, playlist_state)
            return

        # Ensure Apple Music playlist exists
        try:
            apple_music.ensure_playlist(playlist_name)
        except Exception:
            if headless:
                raise
            if input(f'Create Apple Music playlist "{playlist_name}"? [y/N] ').lower() == "y":
                apple_music.ensure_playlist(playlist_name)
            else:
                print("Skipping Apple Music sync.")
                state.update_playlist_order(playlist_state, current_order)
                state.save_playlist_state(backup_dir, playlist_cfg.name, playlist_state)
                return

        # Add newly downloaded + already-downloaded-elsewhere tracks to Apple Music
        all_to_add = {**already_downloaded, **downloaded}
        if all_to_add:
            ordered_paths = []
            for video_id in current_order:
                if video_id in all_to_add:
                    ordered_paths.append(Path(all_to_add[video_id]))
            if ordered_paths:
                print(f"\nAdding {len(ordered_paths)} track(s) to Apple Music...")
                apple_music.add_tracks_to_playlist(ordered_paths, playlist_name)

        if order_changed:
            _reorder_songs(playlist_name, all_synced_songs, current_order)

        state.update_playlist_order(playlist_state, current_order)
        state.save_playlist_state(backup_dir, playlist_cfg.name, playlist_state)

    except KeyboardInterrupt:
        state.save_playlist_state(backup_dir, playlist_cfg.name, playlist_state)
        print("\n[yellow]Sync interrupted. Progress saved.[/yellow]")
        raise


def add_pending_to_apple_music(
    playlist_cfg: PlaylistConfig,
    backup_dir: Path,
) -> None:
    """Add songs that were downloaded but not yet added to Apple Music."""
    playlist_state = state.load_playlist_state(backup_dir, playlist_cfg.name)
    pending = state.get_pending_songs(playlist_state)

    if not pending:
        print(f"No pending songs for '{playlist_cfg.name}'.")
        return

    playlist_name = playlist_cfg.apple_music_playlist
    print(f"\nAdding {len(pending)} pending song(s) to Apple Music playlist '{playlist_name}'...")

    apple_music.ensure_playlist(playlist_name)

    # Add in playlist order where possible
    order = state.get_playlist_order(playlist_state)
    ordered_vids = [vid for vid in order if vid in pending]
    # Any pending not in order (edge case) appended at the end
    ordered_vids += [vid for vid in pending if vid not in order]

    ordered_paths = [Path(pending[vid][const.FILE_PATH_KEY]) for vid in ordered_vids]
    apple_music.add_tracks_to_playlist(ordered_paths, playlist_name)

    for vid in ordered_vids:
        state.mark_apple_music_added(playlist_state, vid)

    state.save_playlist_state(backup_dir, playlist_cfg.name, playlist_state)
    print(f"{len(ordered_paths)} song(s) added to Apple Music.")


def run_sync(
    max_workers: int | None = None,
    dry_run: bool = False,
    playlist_name: str | None = None,
    sync_all: bool = False,
    download_only: bool = False,
    headless: bool = False,
) -> None:
    """Run the sync pipeline for one or more playlists."""
    ensure_dirs()

    playlists, backup_dir, config_max_workers = load_config()
    if max_workers is None:
        max_workers = config_max_workers

    # Migrate legacy global state if present
    if LEGACY_STATE_PATH.exists():
        state.migrate_global_state(LEGACY_STATE_PATH, backup_dir, playlists)

    if playlist_name:
        targets = [pl for pl in playlists if pl.name == playlist_name]
        if not targets:
            available = ", ".join(p.name for p in playlists)
            raise ValueError(
                f"Playlist '{playlist_name}' not in config. Available: {available}"
            )
    elif sync_all:
        targets = playlists
    else:
        targets = [pl for pl in playlists if pl.source == const.LIKED_PLAYLIST_KEY]

    try:
        for cfg in targets:
            print(f"\n--- Syncing: {cfg.name} ---")
            sync_playlist(cfg, backup_dir, playlists, max_workers, dry_run, download_only=download_only, headless=headless)
    except KeyboardInterrupt:
        print("\nSync stopped.")
        return

    print("\nAll syncs complete!")
