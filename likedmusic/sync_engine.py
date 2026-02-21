"""Sync orchestration — coordinates fetching, downloading, and playlist management."""

import re
import shutil
from pathlib import Path

from likedmusic import apple_music, downloader, metadata, state, ytmusic
from likedmusic.config import (
    BACKUP_DIR,
    DOWNLOADS_DIR,
    MAX_DOWNLOAD_WORKERS,
    PLAYLIST_NAME,
    ensure_dirs,
)


def _sanitize_filename(s: str) -> str:
    """Remove characters that are invalid in filenames."""
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def _backup_file(file_path: Path, title: str, artist: str, video_id: str) -> None:
    """Copy M4A to backup directory with human-readable name."""
    safe_artist = _sanitize_filename(artist) if artist else "Unknown"
    safe_title = _sanitize_filename(title)
    backup_name = f"{safe_artist} - {safe_title} [{video_id}].m4a"
    dest = BACKUP_DIR / backup_name
    if not dest.exists():
        shutil.copy2(file_path, dest)


def run_sync(
    max_workers: int = MAX_DOWNLOAD_WORKERS,
    dry_run: bool = False,
) -> None:
    """Run the full sync pipeline."""
    ensure_dirs()

    # 1. Load state
    sync_state = state.load_state()
    synced_ids = state.get_synced_video_ids(sync_state)

    # 2. Fetch liked songs (newest-first)
    print("Fetching liked songs from YouTube Music...")
    tracks = ytmusic.fetch_liked_songs()

    if not tracks:
        print("No liked songs found.")
        return

    # 3. Determine new songs
    new_songs = [t for t in tracks if t.get("videoId") and t["videoId"] not in synced_ids]
    current_order = [t["videoId"] for t in tracks if t.get("videoId")]
    previous_order = sync_state.get("playlist_order", [])
    order_changed = current_order != previous_order

    # Dry-run: preview what would happen, then exit
    if dry_run:
        if new_songs:
            print(f"[DRY RUN] Would download {len(new_songs)} new song(s):")
            for song in new_songs:
                title, artist = metadata.parse_title_artist(
                    song.get("title", ""),
                    song.get("artists"),
                )
                vid = song["videoId"]
                print(f"[DRY RUN]   Would download: {artist} - {title} ({vid})")
            print(
                f'[DRY RUN] Would add {len(new_songs)} track(s) to Apple Music playlist "{PLAYLIST_NAME}"'
            )
        else:
            print("[DRY RUN] No new songs to download.")
        if order_changed:
            print("[DRY RUN] Playlist order would change")
        return

    # 4. Check if already up to date
    if not new_songs and not order_changed:
        print("Already up to date.")
        return

    # 5. Download new songs
    if new_songs:
        print(f"\nDownloading {len(new_songs)} new song(s)...")
        downloaded = downloader.download_songs(new_songs, DOWNLOADS_DIR, max_workers)

        # 6. Embed metadata + 7. Backup + 8. Mark synced
        for song in new_songs:
            video_id = song["videoId"]
            if video_id not in downloaded:
                continue

            file_path = downloaded[video_id]

            # Parse metadata
            title, artist = metadata.parse_title_artist(
                song.get("title", ""),
                song.get("artists"),
            )
            album_info = song.get("album")
            album = album_info.get("name") if album_info and isinstance(album_info, dict) else None
            thumbnail_url = metadata.get_best_thumbnail_url(song.get("thumbnails"))

            # Embed metadata
            print(f"  Tagging: {artist} - {title}")
            metadata.embed_metadata(file_path, title, artist, album, thumbnail_url)

            # Backup
            _backup_file(file_path, title, artist, video_id)

            # Mark synced
            state.mark_synced(sync_state, video_id, title, artist, str(file_path))

        # Save state after downloads
        state.save_state(sync_state)
        print(f"\n{len(downloaded)} song(s) downloaded and tagged.")
    else:
        downloaded = {}

    # 9. Add new songs to Apple Music playlist
    apple_music.ensure_playlist(PLAYLIST_NAME)

    if downloaded:
        # Add new tracks in YTM order (newest first)
        new_ordered_paths = []
        for video_id in current_order:
            if video_id in downloaded:
                new_ordered_paths.append(downloaded[video_id])

        if new_ordered_paths:
            print(f"\nAdding {len(new_ordered_paths)} track(s) to Apple Music...")
            apple_music.add_tracks_to_playlist(new_ordered_paths, PLAYLIST_NAME)

    # 10-11. Handle order changes
    if order_changed:
        print("\nPlaylist order changed, reordering...")
        # Build ordered track names from state
        ordered_names = []
        for video_id in current_order:
            song_info = sync_state.get("synced_songs", {}).get(video_id)
            if song_info:
                ordered_names.append(song_info["title"])

        if ordered_names:
            apple_music.reorder_playlist(PLAYLIST_NAME, ordered_names)
            print("Playlist reordered.")

    # 12. Save final state with updated order
    state.update_playlist_order(sync_state, current_order)
    state.save_state(sync_state)
    print("\nSync complete!")
