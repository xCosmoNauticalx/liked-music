"""Tests for legacy state migration to per-playlist files."""

import json

from likedmusic.state import (
    load_playlist_state,
    migrate_global_state,
)


class TestMigrateGlobalState:
    def test_migrates_single_playlist(self, tmp_path):
        from likedmusic.playlist_config import PlaylistConfig

        legacy = tmp_path / "sync_state.json"
        legacy.write_text(json.dumps({
            "synced_songs": {
                "vid1": {"title": "S1", "artist": "A1", "file_path": "/a", "synced_at": "x"},
            },
            "last_sync": "2026-01-01T00:00:00",
            "playlist_order": ["vid1"],
        }))

        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        playlists = [PlaylistConfig(name="YTM Liked Songs", source="liked")]

        migrate_global_state(legacy, backup_dir, playlists)

        state = load_playlist_state(backup_dir, "YTM Liked Songs")
        assert "vid1" in state["synced_songs"]
        assert state["playlist_order"] == ["vid1"]
        assert not legacy.exists()
        assert (tmp_path / "sync_state.json.migrated").exists()

    def test_migrates_multiple_playlists(self, tmp_path):
        from likedmusic.playlist_config import PlaylistConfig

        legacy = tmp_path / "sync_state.json"
        legacy.write_text(json.dumps({
            "synced_songs": {
                "vid1": {"title": "S1", "artist": "A1", "file_path": "/a", "synced_at": "x"},
                "vid2": {"title": "S2", "artist": "A2", "file_path": "/b", "synced_at": "x"},
                "vid3": {"title": "S3", "artist": "A3", "file_path": "/c", "synced_at": "x"},
            },
            "last_sync": "2026-01-01T00:00:00",
            "playlist_order": ["vid1", "vid2"],
            "playlist_orders": {
                "YTM Liked Songs": ["vid1", "vid2"],
                "EDM": ["vid3"],
            },
        }))

        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        playlists = [
            PlaylistConfig(name="YTM Liked Songs", source="liked"),
            PlaylistConfig(name="EDM", source="EDM"),
        ]

        migrate_global_state(legacy, backup_dir, playlists)

        liked = load_playlist_state(backup_dir, "YTM Liked Songs")
        assert "vid1" in liked["synced_songs"]
        assert "vid2" in liked["synced_songs"]
        assert "vid3" not in liked["synced_songs"]

        edm = load_playlist_state(backup_dir, "EDM")
        assert "vid3" in edm["synced_songs"]
        assert edm["playlist_order"] == ["vid3"]

    def test_unassigned_songs_go_to_first_playlist(self, tmp_path):
        from likedmusic.playlist_config import PlaylistConfig

        legacy = tmp_path / "sync_state.json"
        legacy.write_text(json.dumps({
            "synced_songs": {
                "vid1": {"title": "S1", "artist": "A1", "file_path": "/a", "synced_at": "x"},
                "orphan": {"title": "Orphan", "artist": "?", "file_path": "/o", "synced_at": "x"},
            },
            "last_sync": "2026-01-01T00:00:00",
            "playlist_order": ["vid1"],
        }))

        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        playlists = [PlaylistConfig(name="YTM Liked Songs", source="liked")]

        migrate_global_state(legacy, backup_dir, playlists)

        state = load_playlist_state(backup_dir, "YTM Liked Songs")
        assert "orphan" in state["synced_songs"]

    def test_skips_corrupt_legacy_file(self, tmp_path):
        from likedmusic.playlist_config import PlaylistConfig

        legacy = tmp_path / "sync_state.json"
        legacy.write_text("not json")

        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()

        migrate_global_state(legacy, backup_dir, [PlaylistConfig(name="X", source="liked")])

        # Legacy file should still exist (migration didn't complete)
        assert legacy.exists()
