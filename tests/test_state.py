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
        # Should parse without error
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

    def test_with_playlist_name_writes_to_playlist_orders(self):
        state = {}
        update_playlist_order(state, ["a", "b"], playlist_name="EDM")
        assert state["playlist_orders"]["EDM"] == ["a", "b"]

    def test_with_liked_name_also_writes_top_level(self):
        state = {}
        update_playlist_order(state, ["a", "b"], playlist_name="YTM Liked Songs")
        assert state["playlist_order"] == ["a", "b"]
        assert state["playlist_orders"]["YTM Liked Songs"] == ["a", "b"]

    def test_with_non_liked_name_does_not_write_top_level(self):
        state = {"playlist_order": ["old"]}
        update_playlist_order(state, ["a", "b"], playlist_name="EDM")
        assert state["playlist_order"] == ["old"]


class TestGetPlaylistOrder:
    def test_reads_from_playlist_orders(self):
        state = {"playlist_orders": {"EDM": ["a", "b"]}}
        assert get_playlist_order(state, "EDM") == ["a", "b"]

    def test_fallback_to_top_level_for_liked(self):
        state = {"playlist_order": ["x", "y"]}
        assert get_playlist_order(state, "YTM Liked Songs") == ["x", "y"]

    def test_prefers_playlist_orders_over_top_level(self):
        state = {
            "playlist_order": ["old"],
            "playlist_orders": {"YTM Liked Songs": ["new"]},
        }
        assert get_playlist_order(state, "YTM Liked Songs") == ["new"]

    def test_unknown_playlist_returns_empty(self):
        state = {"playlist_orders": {"EDM": ["a"]}}
        assert get_playlist_order(state, "Unknown") == []

    def test_empty_state_returns_empty(self):
        assert get_playlist_order({}, "anything") == []
