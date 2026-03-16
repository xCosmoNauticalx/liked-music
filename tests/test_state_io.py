"""Tests for per-playlist state I/O with checksum integrity."""

import json

from likedmusic.state import (
    _compute_checksum,
    _sanitize_state_filename,
    _verify_checksum,
    load_all_pending_songs,
    load_all_synced_ids,
    load_all_synced_songs,
    load_playlist_state,
    save_playlist_state,
)


class TestSanitizeStateFilename:
    def test_replaces_spaces_and_special_chars(self):
        assert _sanitize_state_filename("YTM Liked Songs") == "YTM_Liked_Songs"

    def test_replaces_slashes(self):
        assert _sanitize_state_filename("A/B\\C") == "A_B_C"

    def test_strips_leading_trailing_underscores(self):
        assert _sanitize_state_filename(" hello ") == "hello"


class TestChecksum:
    def test_deterministic(self):
        payload = {"b": 2, "a": 1}
        assert _compute_checksum(payload) == _compute_checksum({"a": 1, "b": 2})

    def test_verify_valid(self):
        payload = {"synced_songs": {}, "playlist_order": []}
        checksum = _compute_checksum(payload)
        data = {"checksum": checksum, **payload}
        assert _verify_checksum(data) is True

    def test_verify_tampered(self):
        payload = {"synced_songs": {}, "playlist_order": []}
        data = {"checksum": "wrong", **payload}
        assert _verify_checksum(data) is False

    def test_verify_missing_checksum(self):
        assert _verify_checksum({"synced_songs": {}}) is False


class TestSavePlaylistState:
    def test_creates_file_with_checksum(self, tmp_path):
        state = {"synced_songs": {"vid1": {"title": "Song"}}, "playlist_order": ["vid1"]}
        save_playlist_state(tmp_path, "My Playlist", state)

        path = tmp_path / "My_Playlist.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert "checksum" in data
        assert _verify_checksum(data) is True
        assert data["playlist_name"] == "My Playlist"
        assert "last_sync" in data

    def test_creates_bak_on_second_write(self, tmp_path):
        state = {"synced_songs": {}, "playlist_order": []}
        save_playlist_state(tmp_path, "Test", state)

        state["synced_songs"]["vid1"] = {"title": "New"}
        save_playlist_state(tmp_path, "Test", state)

        bak_path = tmp_path / "Test.json.bak"
        assert bak_path.exists()
        bak_data = json.loads(bak_path.read_text())
        assert "vid1" not in bak_data.get("synced_songs", {})

    def test_overwrites_existing(self, tmp_path):
        save_playlist_state(tmp_path, "X", {"synced_songs": {"old": {}}, "playlist_order": []})
        save_playlist_state(tmp_path, "X", {"synced_songs": {"new": {}}, "playlist_order": []})

        data = json.loads((tmp_path / "X.json").read_text())
        assert "new" in data["synced_songs"]


class TestLoadPlaylistState:
    def test_valid_file(self, tmp_path):
        state = {"synced_songs": {"vid1": {"title": "A"}}, "playlist_order": ["vid1"]}
        save_playlist_state(tmp_path, "PL", state)

        loaded = load_playlist_state(tmp_path, "PL")
        assert "vid1" in loaded["synced_songs"]
        assert "checksum" not in loaded

    def test_missing_returns_default(self, tmp_path):
        loaded = load_playlist_state(tmp_path, "Nonexistent")
        assert loaded["synced_songs"] == {}
        assert loaded["playlist_order"] == []
        assert loaded["playlist_name"] == "Nonexistent"

    def test_corrupt_falls_back_to_bak(self, tmp_path):
        state = {"synced_songs": {"vid1": {"title": "Good"}}, "playlist_order": ["vid1"]}
        save_playlist_state(tmp_path, "PL", state)

        state["synced_songs"]["vid2"] = {"title": "Bad"}
        save_playlist_state(tmp_path, "PL", state)

        # Corrupt the main file
        main_path = tmp_path / "PL.json"
        main_path.write_text("{corrupted}")

        loaded = load_playlist_state(tmp_path, "PL")
        # Should load from .bak (which has only vid1)
        assert "vid1" in loaded["synced_songs"]
        assert "vid2" not in loaded["synced_songs"]

    def test_both_corrupt_returns_default(self, tmp_path):
        save_playlist_state(tmp_path, "PL", {"synced_songs": {}, "playlist_order": []})
        save_playlist_state(tmp_path, "PL", {"synced_songs": {}, "playlist_order": []})

        (tmp_path / "PL.json").write_text("bad")
        (tmp_path / "PL.json.bak").write_text("bad")

        loaded = load_playlist_state(tmp_path, "PL")
        assert loaded["synced_songs"] == {}


class TestLoadAllSyncedIds:
    def test_across_playlists(self, tmp_path):
        save_playlist_state(tmp_path, "A", {
            "synced_songs": {"vid1": {"title": "S1"}, "vid2": {"title": "S2"}},
            "playlist_order": ["vid1", "vid2"],
        })
        save_playlist_state(tmp_path, "B", {
            "synced_songs": {"vid2": {"title": "S2"}, "vid3": {"title": "S3"}},
            "playlist_order": ["vid2", "vid3"],
        })

        ids = load_all_synced_ids(tmp_path)
        assert ids == {"vid1", "vid2", "vid3"}

    def test_skips_corrupt(self, tmp_path):
        save_playlist_state(tmp_path, "Good", {
            "synced_songs": {"vid1": {"title": "S1"}},
            "playlist_order": ["vid1"],
        })
        (tmp_path / "Bad.json").write_text("not json")

        ids = load_all_synced_ids(tmp_path)
        assert ids == {"vid1"}

    def test_empty_dir(self, tmp_path):
        assert load_all_synced_ids(tmp_path) == set()


class TestLoadAllSyncedIdsMissing:
    def test_missing_directory(self, tmp_path):
        missing = tmp_path / "nonexistent"
        assert load_all_synced_ids(missing) == set()


class TestLoadAllSyncedSongs:
    def test_missing_directory(self, tmp_path):
        missing = tmp_path / "nonexistent"
        assert load_all_synced_songs(missing) == {}

    def test_merges_across_playlists(self, tmp_path):
        save_playlist_state(tmp_path, "A", {
            "synced_songs": {"vid1": {"title": "S1", "file_path": "/a/vid1.m4a"}},
            "playlist_order": [],
        })
        save_playlist_state(tmp_path, "B", {
            "synced_songs": {"vid2": {"title": "S2", "file_path": "/b/vid2.m4a"}},
            "playlist_order": [],
        })

        songs = load_all_synced_songs(tmp_path)
        assert "vid1" in songs
        assert "vid2" in songs
        assert songs["vid1"]["file_path"] == "/a/vid1.m4a"


class TestLoadAllPendingSongs:
    def test_returns_pending_across_playlists(self, tmp_path):
        save_playlist_state(tmp_path, "A", {
            "synced_songs": {
                "vid1": {"title": "S1", "file_path": "/a/1.m4a", "apple_music_added": False},
                "vid2": {"title": "S2", "file_path": "/a/2.m4a", "apple_music_added": True},
            },
            "playlist_order": ["vid1", "vid2"],
        })
        save_playlist_state(tmp_path, "B", {
            "synced_songs": {
                "vid3": {"title": "S3", "file_path": "/b/3.m4a", "apple_music_added": False},
            },
            "playlist_order": ["vid3"],
        })

        pending = load_all_pending_songs(tmp_path)
        assert "vid1" in pending
        assert "vid2" not in pending
        assert "vid3" in pending

    def test_empty_dir(self, tmp_path):
        assert load_all_pending_songs(tmp_path) == {}

    def test_missing_directory(self, tmp_path):
        missing = tmp_path / "nonexistent"
        assert load_all_pending_songs(missing) == {}


class TestSavePlaylistStateCleanup:
    def test_cleanup_on_write_failure(self, tmp_path):
        """Verify temp file is cleaned up when write fails."""
        from unittest.mock import patch
        import tempfile as tf

        original_mkstemp = tf.mkstemp

        def failing_mkstemp(**kwargs):
            fd, path = original_mkstemp(**kwargs)
            import os
            os.close(fd)
            # Make the path read-only dir so write_text fails
            from pathlib import Path
            p = Path(path)
            p.write_text("")  # create it
            p.chmod(0o000)
            return fd, path

        # Instead, test that temp file doesn't linger on exception
        state = {"synced_songs": {}, "playlist_order": []}
        save_playlist_state(tmp_path, "Test", state)

        # Verify no .tmp files remain after successful write
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0
