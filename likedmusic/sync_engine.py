"""Sync orchestration — coordinates fetching, downloading, and playlist management."""

import re
import shutil
from typing import List
from pathlib import Path

from likedmusic import apple_music, downloader, metadata, state, ytmusic, const
from likedmusic.config import DOWNLOADS_DIR, ensure_dirs
from likedmusic.playlist_config import PlaylistConfig, load_config, save_config


def _sanitize_filename(s: str) -> str:
    """
    Remove characters that are invalid in filenames.
    
    Replaces characters that are not allowed in filenames across common operating
    systems (Windows, macOS, Linux) with underscores. This ensures the resulting
    string can be safely used as a filename component.
    
    Args:
        s: The input string to sanitize.
    
    Returns:
        A sanitized string with invalid filename characters replaced by underscores.
        The characters replaced are: < > : " / \\ | ? *
    """
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def _backup_file(file_path: Path, title: str, artist: str, video_id: str, backup_dir: Path) -> None:
    """
    Copy an M4A audio file to a backup directory with a human-readable filename.
    
    Creates a backup copy of the downloaded audio file in the specified backup directory.
    The backup filename is formatted as "Artist - Title [VideoID].m4a" with sanitized
    characters to ensure filesystem compatibility. If the backup file already exists,
    no copy is performed.
    
    Args:
        file_path: Path to the source M4A file to be backed up.
        title: The song title, which will be sanitized for use in the filename.
        artist: The artist name, which will be sanitized for use in the filename.
                If empty or None, defaults to "Unknown".
        video_id: The YouTube video ID, used as a unique identifier in the filename.
        backup_dir: Path to the directory where the backup file should be stored.
                    Will be created if it doesn't exist.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe_artist = _sanitize_filename(artist) if artist else "Unknown"
    safe_title = _sanitize_filename(title)
    backup_name = f"{safe_artist} - {safe_title} [{video_id}].m4a"
    dest = backup_dir / backup_name
    if not dest.exists():
        shutil.copy2(file_path, dest)


def _fetch_tracks(playlist_cfg: PlaylistConfig, all_playlists, backup_dir):
    """
    Fetch tracks from YouTube Music for a given playlist configuration.
    
    This function retrieves tracks from either the user's liked songs or a specific
    YouTube Music playlist. If the playlist ID is not already cached in the configuration,
    it resolves the ID from the playlist source name and updates the configuration file.
    
    Args:
        playlist_cfg: A PlaylistConfig object containing the playlist source information
                     and optional cached playlist ID. The source can be either the special
                     "liked" key or a playlist name/URL.
        all_playlists: A list of all PlaylistConfig objects, used when saving the updated
                      configuration after resolving a playlist ID.
        backup_dir: Path to the backup directory, used when saving the updated configuration
                   after resolving a playlist ID.
    
    Returns:
        A list of track dictionaries containing metadata for each song in the playlist.
        Each track dictionary typically includes fields like videoId, title, artists,
        album, and thumbnails. Returns an empty list if no tracks are found.
    """
    if playlist_cfg.source == const.LIKED_PLAYLIST_KEY:
        print("Fetching liked songs from YouTube Music...")
        return ytmusic.fetch_liked_songs()

    # Resolve playlist ID if not cached
    if not playlist_cfg.playlist_id:
        print(f"Resolving playlist ID for '{playlist_cfg.source}'...")
        playlist_cfg.playlist_id = ytmusic.resolve_playlist_id(playlist_cfg.source)
        save_config(all_playlists, backup_dir)
        print(f"Cached playlist ID: {playlist_cfg.playlist_id}")

    print(f"Fetching tracks from '{playlist_cfg.source}'...")
    return ytmusic.fetch_playlist_songs(playlist_cfg.playlist_id)


def _dryrun_new_songs(playlist_name: str, order_changed: bool, new_songs: list[dict] = None) -> None:
    """
    Simulate and display what would happen during a sync operation without making changes.
    
    This function performs a dry run preview of the sync operation, printing information
    about songs that would be downloaded and added to the Apple Music playlist, as well
    as whether the playlist order would change. No actual downloads or playlist modifications
    are performed. This allows users to review the planned changes before executing a real sync.
    
    Args:
        playlist_name: The name of the Apple Music playlist that would receive the new tracks.
                      Used in the output messages to indicate the target playlist.
        order_changed: A boolean flag indicating whether the playlist order would change
                      during the sync operation. If True, prints a message indicating that
                      the playlist order would be updated.
        new_songs: A list of song dictionaries containing metadata for songs that would be
                  downloaded. Each dictionary should include keys like title, artists, and
                  videoId as defined in the YouTube Music API response format. If None or
                  empty, indicates there are no new songs to download. Defaults to None.
    
    Returns:
        None. The function performs side effects by printing dry run information to the
        console, showing what actions would be taken during an actual sync operation.
    """
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
    return


def _reorder_songs(playlist_name: str, sync_state: dict, current_order: List[str]) -> None:
    """
    Reorder tracks in an Apple Music playlist to match the YouTube Music playlist order.
    
    This function updates the track order in an Apple Music playlist to reflect the current
    order of songs in the corresponding YouTube Music playlist. It extracts song titles from
    the sync state based on the provided video IDs and uses them to reorder the Apple Music
    playlist.
    
    Args:
        playlist_name: The name of the Apple Music playlist to reorder.
        sync_state: A dictionary containing the current sync state, including a "synced_songs"
                   key that maps video IDs to song information dictionaries. Each song info
                   dictionary should contain at least a title key (const.TITLE_KEY).
        current_order: A list of YouTube video IDs representing the desired order of tracks
                      in the playlist. The order of IDs in this list determines the final
                      track order in Apple Music.
    
    Returns:
        None. The function performs side effects by reordering the Apple Music playlist
        and printing status messages to the console.
    """
    print("\nPlaylist order changed, reordering...")
    ordered_names = []
    for video_id in current_order:
        song_info = sync_state.get("synced_songs", {}).get(video_id)
        if song_info:
            ordered_names.append(song_info[const.TITLE_KEY])
    if ordered_names:
        apple_music.reorder_playlist(playlist_name, ordered_names)
        print("Playlist reordered.")


def _download_new_songs(new_songs: List[dict], sync_state: dict, max_workers: int, playlist_backup_dir: Path) -> dict[str, Path]:
    """
    Download new songs, embed metadata, create backups, and update sync state.

    Args:
        new_songs: A list of song dictionaries containing metadata for songs to download.
        sync_state: A dictionary containing the current synchronization state.
        max_workers: The maximum number of concurrent worker threads for downloading.
        playlist_backup_dir: Path to the directory where backup copies should be stored.

    Returns:
        A dict mapping video IDs to file paths for successfully downloaded songs.
    """
    print(f"\nDownloading {len(new_songs)} new song(s)...")
    downloaded = downloader.download_songs(new_songs, DOWNLOADS_DIR, max_workers)

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
        _backup_file(file_path, title, artist, video_id, playlist_backup_dir)
        state.mark_synced(sync_state, video_id, title, artist, str(file_path))

    state.save_state(sync_state)
    print(f"\n{len(downloaded)} song(s) downloaded and tagged.")
    return downloaded


def sync_playlist(playlist_cfg: PlaylistConfig, sync_state: dict, backup_dir: Path, all_playlists: list[PlaylistConfig], max_workers: int, dry_run: bool) -> None:
    """
    Synchronize a single playlist from YouTube Music to Apple Music.
    
    This function orchestrates the complete synchronization workflow for a playlist,
    including fetching tracks from YouTube Music, identifying new songs, downloading
    and tagging audio files, creating backups, and updating the corresponding Apple
    Music playlist. It handles both newly downloaded songs and songs that were
    previously downloaded from other playlists. The function also manages playlist
    ordering to ensure the Apple Music playlist matches the YouTube Music playlist
    order.
    
    Args:
        playlist_cfg: A PlaylistConfig object containing the playlist configuration,
                     including the source (YouTube Music playlist name/ID or "liked"),
                     the target Apple Music playlist name, and any cached playlist IDs.
        sync_state: A dictionary containing the current synchronization state, which
                   tracks previously synced songs, their metadata, file paths, and
                   playlist orders. This state is updated during the sync process.
        backup_dir: Path to the root backup directory where playlist-specific backup
                   subdirectories will be created. Each playlist's backups are stored
                   in a subdirectory named after the playlist.
        all_playlists: A list of all PlaylistConfig objects from the configuration file.
                      Used when saving updated configuration after resolving playlist IDs.
        max_workers: The maximum number of concurrent worker threads to use for
                    downloading songs. Higher values enable faster parallel downloads
                    but consume more system resources.
        dry_run: If True, performs a dry run that simulates the sync process without
                actually downloading files, modifying Apple Music playlists, or updating
                the sync state. Prints what actions would be taken instead.
    
    Returns:
        None. The function performs side effects including downloading files, updating
        Apple Music playlists, creating backups, updating the sync state, and printing
        progress messages to the console.
    """
    tracks = _fetch_tracks(playlist_cfg, all_playlists, backup_dir)

    if not tracks:
        print("No tracks found.")
        return

    synced_ids = state.get_synced_video_ids(sync_state)
    synced_songs = sync_state.get(const.SYNCED_SONGS_KEY, {})

    new_songs = [track for track in tracks if track.get(const.VIDEO_ID_KEY) and track[const.VIDEO_ID_KEY] not in synced_ids]
    current_order = [track[const.VIDEO_ID_KEY] for track in tracks if track.get(const.VIDEO_ID_KEY)]
    previous_order = state.get_playlist_order(sync_state, playlist_cfg.name)
    order_changed = current_order != previous_order

    # Find songs already downloaded (from another playlist) that need adding
    # to this playlist's Apple Music playlist
    already_downloaded = {
        vid: synced_songs[vid][const.FILE_PATH_KEY]
        for vid in current_order
        if vid in synced_ids and vid not in {track[const.VIDEO_ID_KEY] for track in new_songs}
    }

    playlist_name = playlist_cfg.apple_music_playlist

    if dry_run:
        _dryrun_new_songs(playlist_name, order_changed, new_songs)
        return

    if not new_songs and not order_changed:
        print("Already up to date.")
        return

    playlist_backup_dir = backup_dir / playlist_cfg.name
    downloaded = {}

    if new_songs:
        downloaded = _download_new_songs(new_songs, sync_state, max_workers, playlist_backup_dir)

    # Ensure Apple Music playlist exists, prompt to create if needed
    try:
        apple_music.ensure_playlist(playlist_name)
    except Exception:
        if input(f'Create Apple Music playlist "{playlist_name}"? [y/N] ').lower() == "y":
            apple_music.ensure_playlist(playlist_name)
        else:
            print("Skipping Apple Music sync.")
            state.update_playlist_order(sync_state, current_order, playlist_cfg.name)
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
        _reorder_songs(playlist_name, sync_state, current_order)

    state.update_playlist_order(sync_state, current_order, playlist_cfg.name)


def run_sync(max_workers: int | None = None, dry_run: bool = False, playlist_name: str | None = None, sync_all: bool = False) -> None:
    """
    Execute the synchronization pipeline for one or more playlists from YouTube Music to Apple Music.
    
    This function serves as the main entry point for the sync operation. It orchestrates the
    complete synchronization workflow by loading configuration and state, determining which
    playlists to sync based on the provided parameters, and executing the sync process for
    each target playlist. The function handles three sync modes: syncing a specific playlist
    by name, syncing all configured playlists, or syncing only the "liked" songs playlist
    (default behavior).
    
    Args:
        max_workers: The maximum number of concurrent worker threads to use for downloading
                    songs. Higher values enable faster parallel downloads but consume more
                    system resources. Defaults to MAX_DOWNLOAD_WORKERS from the configuration.
        dry_run: If True, performs a dry run that simulates the sync process without actually
                downloading files, modifying Apple Music playlists, or updating the sync state.
                Prints what actions would be taken instead. Defaults to False.
        playlist_name: The name of a specific playlist to sync. If provided, only the playlist
                      with this exact name will be synced. If the name doesn't match any
                      configured playlist, raises a ValueError with available playlist names.
                      Defaults to None.
        sync_all: If True, syncs all playlists defined in the configuration file. This parameter
                 is ignored if playlist_name is specified. If both playlist_name and sync_all
                 are False/None, only the "liked" songs playlist is synced. Defaults to False.
    
    Returns:
        None. The function performs side effects including downloading files, updating Apple
        Music playlists, creating backups, updating the sync state, and printing progress
        messages to the console.
    
    Raises:
        ValueError: If playlist_name is specified but no matching playlist is found in the
                   configuration. The error message includes a list of available playlist names.
    """
    ensure_dirs()

    sync_state = state.load_state()
    playlists, backup_dir, config_max_workers = load_config()
    if max_workers is None:
        max_workers = config_max_workers

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

    for cfg in targets:
        print(f"\n--- Syncing: {cfg.name} ---")
        sync_playlist(cfg, sync_state, backup_dir, playlists, max_workers, dry_run)

    if not dry_run:
        state.save_state(sync_state)
    print("\nAll syncs complete!")
