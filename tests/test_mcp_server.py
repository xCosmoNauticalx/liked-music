"""Tests for the MCP server module."""

import asyncio
import io
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from likedmusic.mcp_server import (
    _validate_prerequisites,
    _redirect_stdout,
    _list_playlists_sync,
    _get_playlist_status_sync,
    _get_sync_history_sync,
    _dry_run_sync_sync,
    _sync_playlist_sync,
    _sync_playlist_download_only_sync,
    list_playlists,
    get_playlist_status,
    get_sync_history,
    dry_run_sync,
    sync_playlist,
    sync_playlist_download_only,
)
from likedmusic.playlist_config import PlaylistConfig


_DEFAULT_PLAYLISTS = [
    PlaylistConfig(name="YTM Liked Songs", source="liked", apple_music_playlist="YTM Liked Songs"),
    PlaylistConfig(name="Chill", source="chill_vibes", playlist_id="PL123", apple_music_playlist="Chill Vibes"),
]
_DEFAULT_BACKUP_DIR = Path("/tmp/backup")

_EMPTY_STATE = {
    "playlist_name": "YTM Liked Songs",
    "last_sync": None,
    "playlist_order": [],
    "synced_songs": {},
}

_POPULATED_STATE = {
    "playlist_name": "YTM Liked Songs",
    "last_sync": "2026-03-13T10:00:00+00:00",
    "playlist_order": ["vid1", "vid2"],
    "synced_songs": {
        "vid1": {
            "title": "Song1",
            "artist": "Artist1",
            "file_path": "/tmp/vid1.m4a",
            "synced_at": "2026-03-13T10:00:00+00:00",
            "apple_music_added": True,
        },
        "vid2": {
            "title": "Song2",
            "artist": "Artist2",
            "file_path": "/tmp/vid2.m4a",
            "synced_at": "2026-03-13T09:00:00+00:00",
            "apple_music_added": False,
        },
    },
}


class TestValidatePrerequisites:
    def test_missing_browser_json_raises(self):
        with patch("likedmusic.mcp_server.BROWSER_AUTH_PATH") as mock_path:
            mock_path.is_file.return_value = False
            with pytest.raises(FileNotFoundError, match="browser.json"):
                _validate_prerequisites()

    def test_missing_config_yml_raises(self):
        with (
            patch("likedmusic.mcp_server.BROWSER_AUTH_PATH") as mock_browser,
            patch("likedmusic.mcp_server.CONFIG_PATH") as mock_config,
        ):
            mock_browser.is_file.return_value = True
            mock_config.is_file.return_value = False
            with pytest.raises(FileNotFoundError, match="config.yml"):
                _validate_prerequisites()

    def test_both_present_succeeds(self):
        with (
            patch("likedmusic.mcp_server.BROWSER_AUTH_PATH") as mock_browser,
            patch("likedmusic.mcp_server.CONFIG_PATH") as mock_config,
        ):
            mock_browser.is_file.return_value = True
            mock_config.is_file.return_value = True
            _validate_prerequisites()  # Should not raise


class TestRedirectStdout:
    def test_captures_print_output(self):
        with _redirect_stdout() as buf:
            print("hello from sync")
        assert "hello from sync" in buf.getvalue()

    def test_restores_stdout(self):
        original = sys.stdout
        with _redirect_stdout():
            pass
        assert sys.stdout is original

    def test_restores_stdout_on_exception(self):
        original = sys.stdout
        with pytest.raises(RuntimeError):
            with _redirect_stdout():
                raise RuntimeError("boom")
        assert sys.stdout is original


def _patch_prereqs():
    """Patch prerequisite checks to pass."""
    return (
        patch("likedmusic.mcp_server.BROWSER_AUTH_PATH", **{"is_file.return_value": True}),
        patch("likedmusic.mcp_server.CONFIG_PATH", **{"is_file.return_value": True}),
    )


class TestListPlaylists:
    def test_returns_playlist_info(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=(_DEFAULT_PLAYLISTS, _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_POPULATED_STATE}),
        ):
            result = _list_playlists_sync()

        assert "playlists" in result
        assert len(result["playlists"]) == 2
        first = result["playlists"][0]
        assert first["name"] == "YTM Liked Songs"
        assert first["synced_count"] == 2
        assert first["pending_count"] == 1
        assert first["last_sync"] == "2026-03-13T10:00:00+00:00"

    def test_empty_state(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=([_DEFAULT_PLAYLISTS[0]], _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_EMPTY_STATE}),
        ):
            result = _list_playlists_sync()

        assert result["playlists"][0]["synced_count"] == 0
        assert result["playlists"][0]["pending_count"] == 0


class TestGetPlaylistStatus:
    def test_returns_status(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=(_DEFAULT_PLAYLISTS, _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_POPULATED_STATE}),
        ):
            result = _get_playlist_status_sync("YTM Liked Songs")

        assert result["name"] == "YTM Liked Songs"
        assert result["synced_count"] == 2
        assert result["pending_count"] == 1
        assert result["track_order_count"] == 2

    def test_unknown_playlist_raises(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=(_DEFAULT_PLAYLISTS, _DEFAULT_BACKUP_DIR, 4)),
        ):
            with pytest.raises(ValueError, match="not found"):
                _get_playlist_status_sync("Nonexistent")


class TestGetSyncHistory:
    def test_returns_sorted_history(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=([_DEFAULT_PLAYLISTS[0]], _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_POPULATED_STATE}),
        ):
            result = _get_sync_history_sync(limit=10)

        assert result["total_synced"] == 2
        history = result["history"]
        assert len(history) == 2
        # Most recent first
        assert history[0]["video_id"] == "vid1"
        assert history[1]["video_id"] == "vid2"

    def test_respects_limit(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=([_DEFAULT_PLAYLISTS[0]], _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_POPULATED_STATE}),
        ):
            result = _get_sync_history_sync(limit=1)

        assert len(result["history"]) == 1
        assert result["total_synced"] == 2


class TestDryRunSync:
    def test_calls_run_sync_with_dry_run(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync") as mock_run,
        ):
            result = _dry_run_sync_sync("YTM Liked Songs")

        mock_run.assert_called_once_with(
            dry_run=True,
            playlist_name="YTM Liked Songs",
            sync_all=False,
            headless=True,
        )
        assert result["status"] == "dry_run_complete"

    def test_syncs_all_when_no_name(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync") as mock_run,
        ):
            _dry_run_sync_sync(None)

        mock_run.assert_called_once_with(
            dry_run=True,
            playlist_name=None,
            sync_all=True,
            headless=True,
        )

    def test_captures_stdout(self):
        p1, p2 = _patch_prereqs()
        def fake_run(**kwargs):
            print("Would download 3 songs")

        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync", side_effect=fake_run),
        ):
            result = _dry_run_sync_sync("Test")

        assert "Would download 3 songs" in result["log"]


class TestSyncPlaylist:
    def test_calls_run_sync_with_headless(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync") as mock_run,
        ):
            result = _sync_playlist_sync("YTM Liked Songs")

        mock_run.assert_called_once_with(
            playlist_name="YTM Liked Songs",
            sync_all=False,
            headless=True,
        )
        assert result["status"] == "success"

    def test_syncs_all_when_no_name(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync") as mock_run,
        ):
            _sync_playlist_sync(None)

        mock_run.assert_called_once_with(
            playlist_name=None,
            sync_all=True,
            headless=True,
        )

    def test_captures_stdout(self):
        p1, p2 = _patch_prereqs()
        def fake_run(**kwargs):
            print("Downloading 5 songs...")

        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync", side_effect=fake_run),
        ):
            result = _sync_playlist_sync("Test")

        assert "Downloading 5 songs" in result["log"]


class TestSyncPlaylistDownloadOnly:
    def test_calls_run_sync_download_only(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync") as mock_run,
        ):
            result = _sync_playlist_download_only_sync("YTM Liked Songs")

        mock_run.assert_called_once_with(
            playlist_name="YTM Liked Songs",
            sync_all=False,
            download_only=True,
            headless=True,
        )
        assert result["status"] == "success"


class TestAsyncTools:
    """Verify async tool wrappers delegate correctly."""

    def test_list_playlists_async(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=([_DEFAULT_PLAYLISTS[0]], _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_EMPTY_STATE}),
        ):
            result = asyncio.run(list_playlists())
        assert "playlists" in result

    def test_get_playlist_status_async(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.mcp_server.load_config", return_value=(_DEFAULT_PLAYLISTS, _DEFAULT_BACKUP_DIR, 4)),
            patch("likedmusic.mcp_server.state.load_playlist_state", return_value={**_POPULATED_STATE}),
        ):
            result = asyncio.run(get_playlist_status("YTM Liked Songs"))
        assert result["name"] == "YTM Liked Songs"

    def test_sync_playlist_async(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync"),
        ):
            result = asyncio.run(sync_playlist("Test"))
        assert result["status"] == "success"

    def test_dry_run_async(self):
        p1, p2 = _patch_prereqs()
        with (
            p1, p2,
            patch("likedmusic.sync_engine.run_sync"),
        ):
            result = asyncio.run(dry_run_sync("Test"))
        assert result["status"] == "dry_run_complete"
