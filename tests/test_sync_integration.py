"""Integration tests for likedmusic.sync_engine.run_sync."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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

_EMPTY_STATE = {
    "playlist_name": "YTM Liked Songs",
    "last_sync": None,
    "playlist_order": [],
    "synced_songs": {},
}


def _base_patches():
    """Return a dict of common patches for run_sync integration tests."""
    return {
        "ensure_dirs": patch("likedmusic.sync_engine.ensure_dirs"),
        "load_playlist_state": patch("likedmusic.sync_engine.state.load_playlist_state"),
        "save_playlist_state": patch("likedmusic.sync_engine.state.save_playlist_state"),
        "load_all_synced_ids": patch("likedmusic.sync_engine.state.load_all_synced_ids", return_value=set()),
        "load_all_synced_songs": patch("likedmusic.sync_engine.state.load_all_synced_songs", return_value={}),
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
        "legacy_state": patch("likedmusic.sync_engine.LEGACY_STATE_PATH", new_callable=lambda: type("P", (), {"exists": staticmethod(lambda: False)})),
        "dashboard": patch("likedmusic.dashboard.DownloadDashboard"),
    }


class TestSyncHappyPath:
    def test_new_songs_downloaded_tagged_added(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"] as mock_save,
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"] as mock_embed,
            patches["ensure_playlist"] as mock_ensure_pl,
            patches["add_tracks_to_playlist"] as mock_add_tracks,
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
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
            assert mock_save.call_count >= 2

    def test_incremental_sync_skips_already_synced(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"],
            patches["load_all_synced_ids"] as mock_ids,
            patches["load_all_synced_songs"] as mock_songs,
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {
                "playlist_name": "YTM Liked Songs",
                "synced_songs": {"vid1": {"title": "Song1", "artist": "A1", "file_path": "/x", "synced_at": "x"}},
                "last_sync": None,
                "playlist_order": ["vid1"],
            }
            mock_ids.return_value = {"vid1"}
            mock_songs.return_value = {"vid1": {"title": "Song1", "file_path": "/x"}}
            mock_fetch.return_value = [FAKE_SONGS[0]]

            run_sync()

            mock_dl.assert_not_called()

    def test_order_change_triggers_reorder(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"],
            patches["load_all_synced_ids"] as mock_ids,
            patches["load_all_synced_songs"] as mock_songs,
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"] as mock_reorder,
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {
                "playlist_name": "YTM Liked Songs",
                "synced_songs": {
                    "vid1": {"title": "Song1", "artist": "A1", "file_path": "/x", "synced_at": "x"},
                    "vid2": {"title": "Song2", "artist": "A2", "file_path": "/y", "synced_at": "y"},
                },
                "last_sync": None,
                "playlist_order": ["vid1", "vid2"],
            }
            mock_ids.return_value = {"vid1", "vid2"}
            mock_songs.return_value = {
                "vid1": {"title": "Song1", "file_path": "/x"},
                "vid2": {"title": "Song2", "file_path": "/y"},
            }
            mock_fetch.return_value = list(reversed(FAKE_SONGS))

            run_sync()

            mock_reorder.assert_called_once()

    def test_empty_liked_songs_returns_early(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"] as mock_save,
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
            mock_fetch.return_value = []

            run_sync()

            mock_dl.assert_not_called()
            mock_save.assert_not_called()


class TestDryRun:
    def test_dry_run_no_downloads(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"],
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            mock_dl.assert_not_called()

    def test_dry_run_no_applescript(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"],
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"] as mock_ensure_pl,
            patches["add_tracks_to_playlist"] as mock_add_tracks,
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            mock_ensure_pl.assert_not_called()
            mock_add_tracks.assert_not_called()

    def test_dry_run_state_unchanged(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"] as mock_save,
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
            mock_fetch.return_value = FAKE_SONGS

            run_sync(dry_run=True)

            mock_save.assert_not_called()

    def test_dry_run_output(self, capsys):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"],
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
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
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"],
            patches["load_all_synced_ids"] as mock_ids,
            patches["load_all_synced_songs"] as mock_songs,
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"],
            patches["embed_metadata"],
            patches["ensure_playlist"],
            patches["add_tracks_to_playlist"],
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {
                "playlist_name": "YTM Liked Songs",
                "synced_songs": {
                    "vid1": {"title": "Song1", "artist": "A1", "file_path": "/x", "synced_at": "x"},
                    "vid2": {"title": "Song2", "artist": "A2", "file_path": "/y", "synced_at": "y"},
                },
                "last_sync": None,
                "playlist_order": ["vid1", "vid2"],
            }
            mock_ids.return_value = {"vid1", "vid2"}
            mock_songs.return_value = {
                "vid1": {"title": "Song1", "file_path": "/x"},
                "vid2": {"title": "Song2", "file_path": "/y"},
            }
            mock_fetch.return_value = list(reversed(FAKE_SONGS))

            run_sync(dry_run=True)

            captured = capsys.readouterr()
            assert "Playlist order would change" in captured.out


class TestDownloadOnlyMode:
    def test_download_only_skips_apple_music(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["load_playlist_state"] as mock_load,
            patches["save_playlist_state"] as mock_save,
            patches["load_all_synced_ids"],
            patches["load_all_synced_songs"],
            patches["fetch_liked_songs"] as mock_fetch,
            patches["download_songs"] as mock_dl,
            patches["embed_metadata"],
            patches["ensure_playlist"] as mock_ensure_pl,
            patches["add_tracks_to_playlist"] as mock_add_tracks,
            patches["reorder_playlist"],
            patches["backup_file"],
            patches["legacy_state"],
        ):
            mock_load.return_value = {**_EMPTY_STATE}
            mock_fetch.return_value = FAKE_SONGS
            mock_dl.return_value = {
                "vid1": Path("/tmp/vid1.m4a"),
                "vid2": Path("/tmp/vid2.m4a"),
            }

            run_sync(download_only=True)

            mock_dl.assert_called_once()
            mock_ensure_pl.assert_not_called()
            mock_add_tracks.assert_not_called()
            assert mock_save.call_count >= 1


class TestRunSyncBranches:
    def test_sync_all_targets_all_playlists(self):
        multi_playlists = [
            PlaylistConfig(name="YTM Liked Songs", source="liked", apple_music_playlist="YTM Liked Songs"),
            PlaylistConfig(name="EDM", source="EDM", playlist_id="PL_edm", apple_music_playlist="EDM"),
        ]
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patch(
                "likedmusic.sync_engine.load_config",
                return_value=(multi_playlists, _DEFAULT_BACKUP_DIR, 4),
            ),
            patch("likedmusic.sync_engine.sync_playlist") as mock_sync_pl,
            patches["legacy_state"],
        ):
            run_sync(sync_all=True)
            assert mock_sync_pl.call_count == 2

    def test_playlist_name_filters_to_one(self):
        multi_playlists = [
            PlaylistConfig(name="YTM Liked Songs", source="liked", apple_music_playlist="YTM Liked Songs"),
            PlaylistConfig(name="EDM", source="EDM", playlist_id="PL_edm", apple_music_playlist="EDM"),
        ]
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patch(
                "likedmusic.sync_engine.load_config",
                return_value=(multi_playlists, _DEFAULT_BACKUP_DIR, 4),
            ),
            patch("likedmusic.sync_engine.sync_playlist") as mock_sync_pl,
            patches["legacy_state"],
        ):
            run_sync(playlist_name="EDM")
            mock_sync_pl.assert_called_once()
            assert mock_sync_pl.call_args[0][0].name == "EDM"

    def test_unknown_playlist_raises(self):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patches["legacy_state"],
        ):
            with pytest.raises(ValueError, match="not in config"):
                run_sync(playlist_name="Nonexistent")

    def test_keyboard_interrupt_stops_gracefully(self, capsys):
        patches = _base_patches()
        with (
            patches["ensure_dirs"],
            patches["load_config"],
            patch("likedmusic.sync_engine.sync_playlist", side_effect=KeyboardInterrupt),
            patches["legacy_state"],
        ):
            run_sync()
            captured = capsys.readouterr()
            assert "Sync stopped" in captured.out


class TestAddPendingToAppleMusic:
    def test_adds_pending_songs(self):
        from likedmusic.sync_engine import add_pending_to_apple_music

        pl = PlaylistConfig(name="Test", source="liked", apple_music_playlist="Test")

        with (
            patch("likedmusic.sync_engine.state.load_playlist_state") as mock_load,
            patch("likedmusic.sync_engine.state.get_pending_songs") as mock_pending,
            patch("likedmusic.sync_engine.state.get_playlist_order", return_value=["vid1"]),
            patch("likedmusic.sync_engine.state.mark_apple_music_added") as mock_mark,
            patch("likedmusic.sync_engine.state.save_playlist_state") as mock_save,
            patch("likedmusic.sync_engine.apple_music.ensure_playlist") as mock_ensure,
            patch("likedmusic.sync_engine.apple_music.add_tracks_to_playlist") as mock_add,
        ):
            mock_load.return_value = {"synced_songs": {"vid1": {"file_path": "/tmp/1.m4a", "apple_music_added": False}}}
            mock_pending.return_value = {"vid1": {"file_path": "/tmp/1.m4a", "apple_music_added": False}}

            add_pending_to_apple_music(pl, Path("/tmp/backup"))

            mock_ensure.assert_called_once_with("Test")
            mock_add.assert_called_once()
            mock_mark.assert_called_once_with(mock_load.return_value, "vid1")
            mock_save.assert_called_once()

    def test_no_pending_returns_early(self):
        from likedmusic.sync_engine import add_pending_to_apple_music

        pl = PlaylistConfig(name="Test", source="liked", apple_music_playlist="Test")

        with (
            patch("likedmusic.sync_engine.state.load_playlist_state") as mock_load,
            patch("likedmusic.sync_engine.state.get_pending_songs", return_value={}),
            patch("likedmusic.sync_engine.apple_music.ensure_playlist") as mock_ensure,
        ):
            mock_load.return_value = {"synced_songs": {}}

            add_pending_to_apple_music(pl, Path("/tmp/backup"))

            mock_ensure.assert_not_called()


class TestSyncEngineHelpers:
    def test_backup_file_copies_to_backup_dir(self, tmp_path):
        from likedmusic.sync_engine import _backup_file

        src = tmp_path / "song.m4a"
        src.write_text("audio data")
        backup_dir = tmp_path / "Backup"

        _backup_file(src, "Song Title", "Artist", "vid1", backup_dir)

        dest = backup_dir / "Artist - Song Title [vid1].m4a"
        assert dest.exists()
        assert dest.read_text() == "audio data"

    def test_backup_file_skips_existing(self, tmp_path):
        from likedmusic.sync_engine import _backup_file

        src = tmp_path / "song.m4a"
        src.write_text("new data")
        backup_dir = tmp_path / "Backup"
        backup_dir.mkdir()
        dest = backup_dir / "Artist - Title [vid1].m4a"
        dest.write_text("old data")

        _backup_file(src, "Title", "Artist", "vid1", backup_dir)

        assert dest.read_text() == "old data"

    def test_fetch_tracks_liked(self):
        from likedmusic.sync_engine import _fetch_tracks

        pl = PlaylistConfig(name="YTM Liked Songs", source="liked", apple_music_playlist="YTM Liked Songs")
        with patch("likedmusic.sync_engine.ytmusic.fetch_liked_songs", return_value=[{"videoId": "v1"}]) as mock_fetch:
            result = _fetch_tracks(pl, [], Path("/tmp/backup"))
        assert result == [{"videoId": "v1"}]
        mock_fetch.assert_called_once()

    def test_fetch_tracks_resolves_playlist_id(self):
        from likedmusic.sync_engine import _fetch_tracks

        pl = PlaylistConfig(name="EDM", source="EDM", playlist_id=None, apple_music_playlist="EDM")
        all_playlists = [pl]
        with (
            patch("likedmusic.sync_engine.ytmusic.resolve_playlist_id", return_value="PL_resolved") as mock_resolve,
            patch("likedmusic.sync_engine.ytmusic.fetch_playlist_songs", return_value=[{"videoId": "v2"}]) as mock_fetch,
            patch("likedmusic.sync_engine.save_config"),
        ):
            result = _fetch_tracks(pl, all_playlists, Path("/tmp/backup"))
        assert result == [{"videoId": "v2"}]
        mock_resolve.assert_called_once_with("EDM")
        assert pl.playlist_id == "PL_resolved"
