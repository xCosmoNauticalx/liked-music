"""Tests for likedmusic.state — pure state manipulation functions."""

from datetime import datetime

from likedmusic.state import (
    get_playlist_order,
    get_synced_video_ids,
    mark_synced,
    update_playlist_order,
)


class TestGetSyncedVideoIds:
    def test_populated_dict(self):
        state = {"synced_songs": {"abc": {}, "def": {}}}
        assert get_synced_video_ids(state) == {"abc", "def"}

    def test_empty_dict(self):
        state = {"synced_songs": {}}
        assert get_synced_video_ids(state) == set()

    def test_missing_synced_songs_key(self):
        state = {}
        assert get_synced_video_ids(state) == set()


class TestMarkSynced:
    def test_adds_entry_with_correct_fields(self):
        state = {"synced_songs": {}}
        mark_synced(state, "vid1", "Title", "Artist", "/path/to/file.m4a")
        entry = state["synced_songs"]["vid1"]
        assert entry["title"] == "Title"
        assert entry["artist"] == "Artist"
        assert entry["file_path"] == "/path/to/file.m4a"
        assert "synced_at" in entry

    def test_synced_at_is_iso_timestamp(self):
        state = {"synced_songs": {}}
        mark_synced(state, "vid1", "Title", "Artist", "/path")
        ts = state["synced_songs"]["vid1"]["synced_at"]
        datetime.fromisoformat(ts)

    def test_creates_synced_songs_key_if_missing(self):
        state = {}
        mark_synced(state, "vid1", "Title", "Artist", "/path")
        assert "vid1" in state["synced_songs"]


class TestUpdatePlaylistOrder:
    def test_sets_playlist_order(self):
        state = {}
        update_playlist_order(state, ["a", "b", "c"])
        assert state["playlist_order"] == ["a", "b", "c"]

    def test_overwrites_existing_order(self):
        state = {"playlist_order": ["x"]}
        update_playlist_order(state, ["a", "b"])
        assert state["playlist_order"] == ["a", "b"]


class TestGetPlaylistOrder:
    def test_reads_order(self):
        state = {"playlist_order": ["a", "b"]}
        assert get_playlist_order(state) == ["a", "b"]

    def test_empty_state_returns_empty(self):
        assert get_playlist_order({}) == []

    def test_missing_key_returns_empty(self):
        state = {"synced_songs": {}}
        assert get_playlist_order(state) == []
