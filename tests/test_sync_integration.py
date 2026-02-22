"""Integration tests for likedmusic.sync_engine.run_sync."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from likedmusic.playlist_config import PlaylistConfig
from likedmusic.sync_engine import run_sync

_DEFAULT_PLAYLISTS = [
    PlaylistConfig(name="YTM Liked Songs", source="liked", apple_music_playlist="YTM Liked Songs")
]
_DEFAULT_BACKUP_DIR = Path("/tmp/backup")

FAKE_SONGS = [
    {
        "videoId": "vid1",
        "title": "Artist1 - Song1",
        "artists": [],
        "album": {"name": "Album1"},
        "thumbnails": [{"url": "http://img.com/1.jpg", "width": 120}],
    },
    {
        "videoId": "vid2",
        "title": "Song2",
        "artists": [{"name": "Artist2"}],
        "album": None,
        "thumbnails": None,
    },
]


def _base_patches():
    """Return a dict of common patches for run_sync integration tests."""
    return {
        "ensure_dirs": patch("likedmusic.sync_engine.ensure_dirs"),
        "load_state": patch("likedmusic.sync_engine.state.load_state"),
        "save_state": patch("likedmusic.sync_engine.state.save_state"),
        "fetch_liked_songs": patch("likedmusic.sync_engine.ytmusic.fetch_liked_songs"),
        "download_songs": patch("likedmusic.sync_engine.downloader.download_songs"),
        "embed_metadata": patch("likedmusic.sync_engine.metadata.embed_metadata"),
        "ensure_playlist": patch("likedmusic.sync_engine.apple_music.ensure_playlist"),
        "add_tracks_to_playlist": patch("likedmusic.sync_engine.apple_music.add_tracks_to_playlist"),
        "reorder_playlist": patch("likedmusic.sync_engine.apple_music.reorder_playlist"),
        "backup_file": patch("likedmusic.sync_engine._backup_file"),
        "load_config": patch(
            "likedmusic.sync_engine.load_config",
            return_value=(_DEFAULT_PLAYLISTS, _DEFAULT_BACKUP_DIR, 4),
        ),
    }


class TestSyncHappyPath:
    def test_new_songs_downloaded_tagged_added(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"] as mock_save,
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"] as mock_embed,
            patches["ensure_playlist"] as mock_ensure_pl,
            patches["add_tracks_to_playlist"] as mock_add_tracks,
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {"synced_songs": {}, "last_sync": None, "playlist_order": []}
            mock_fetch.return_value = FAKE_SONGS
            mock_dl.return_value = {
                "vid1": Path("/tmp/vid1.m4a"),
                "vid2": Path("/tmp/vid2.m4a"),
            }

            run_sync()

            mock_dl.assert_called_once()
            assert mock_embed.call_count == 2
            mock_ensure_pl.assert_called_once()
            mock_add_tracks.assert_called_once()
            assert mock_save.call_count == 2  # after downloads + after order

    def test_incremental_sync_skips_already_synced(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {
                "synced_songs": {
                    "vid1": {"title": "Song1", "artist": "Artist1", "file_path": "/tmp/vid1.m4a", "synced_at": "x"},
                },
                "last_sync": None,
                "playlist_order": ["vid1"],
            }
            mock_fetch.return_value = [FAKE_SONGS[0]]  # only vid1
            mock_dl.return_value = {}

            run_sync()

            # No new songs to download, order unchanged -> "Already up to date"
            mock_dl.assert_not_called()

    def test_order_change_triggers_reorder(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"] as mock_reorder,
            patches["backup_file"],
        ):
            mock_load.return_value = {
                "synced_songs": {
                    "vid1": {"title": "Song1", "artist": "Artist1", "file_path": "/x", "synced_at": "x"},
                    "vid2": {"title": "Song2", "artist": "Artist2", "file_path": "/y", "synced_at": "y"},
                },
                "last_sync": None,
                "playlist_order": ["vid1", "vid2"],  # old order
            }
            # Return songs in reversed order
            mock_fetch.return_value = list(reversed(FAKE_SONGS))

            run_sync()

            mock_reorder.assert_called_once()

    def test_empty_liked_songs_returns_early(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"] as mock_save,
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {"synced_songs": {}, "last_sync": None, "playlist_order": []}
            mock_fetch.return_value = []

            run_sync()

            mock_dl.assert_not_called()
            # save_state is called once at end of run_sync (final state persist)
            mock_save.assert_called_once()


class TestDryRun:
    def test_dry_run_no_downloads(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {"synced_songs": {}, "last_sync": None, "playlist_order": []}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            mock_dl.assert_not_called()

    def test_dry_run_no_applescript(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"] as mock_ensure_pl,
            patches["add_tracks_to_playlist"] as mock_add_tracks,
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {"synced_songs": {}, "last_sync": None, "playlist_order": []}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            mock_ensure_pl.assert_not_called()
            mock_add_tracks.assert_not_called()

    def test_dry_run_state_unchanged(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"] as mock_save,
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {"synced_songs": {}, "last_sync": None, "playlist_order": []}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            mock_save.assert_not_called()

    def test_dry_run_output(self, capsys):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {"synced_songs": {}, "last_sync": None, "playlist_order": []}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "Would download 2 new song(s)" in captured.out
            assert "vid1" in captured.out
            assert "vid2" in captured.out

    def test_dry_run_order_change_message(self, capsys):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_state"] as mock_load,
            patches["save_state"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
        ):
            mock_load.return_value = {
                "synced_songs": {
                    "vid1": {"title": "Song1", "artist": "A1", "file_path": "/x", "synced_at": "x"},
                    "vid2": {"title": "Song2", "artist": "A2", "file_path": "/y", "synced_at": "y"},
                },
                "last_sync": None,
                "playlist_order": ["vid1", "vid2"],
            }
            mock_fetch.return_value = list(reversed(FAKE_SONGS))

            run_sync(dry_run=True)

            captured = capsys.readouterr()
            assert "Playlist order would change" in captured.out
