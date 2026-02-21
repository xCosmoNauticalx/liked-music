"""Tests for likedmusic.apple_music — AppleScript wrappers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from likedmusic.apple_music import (
    _escape_applescript_string,
    add_track_to_playlist,
    ensure_playlist,
    run_applescript,
)


class TestEscapeApplescriptString:
    def test_backslash_escaping(self):
        assert _escape_applescript_string("a\\b") == "a\\\\b"

    def test_quote_escaping(self):
        assert _escape_applescript_string('say "hello"') == 'say \\"hello\\"'

    def test_combined(self):
        assert _escape_applescript_string('a\\b"c') == 'a\\\\b\\"c'

    def test_no_special_chars(self):
        assert _escape_applescript_string("plain text") == "plain text"


class TestEnsurePlaylist:
    @patch("likedmusic.apple_music.subprocess.run")
    def test_calls_osascript(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        ensure_playlist("My Playlist")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "osascript"
        assert "My Playlist" in args[2]


class TestAddTrackToPlaylist:
    @patch("likedmusic.apple_music.subprocess.run")
    def test_passes_posix_path(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        add_track_to_playlist(Path("/tmp/song.m4a"), "Playlist")
        args = mock_run.call_args[0][0]
        assert "POSIX file" in args[2]
        assert "/tmp/song.m4a" in args[2]


class TestRunApplescript:
    @patch("likedmusic.apple_music.subprocess.run")
    def test_raises_on_nonzero_exit(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="script error"
        )
        with pytest.raises(RuntimeError, match="AppleScript failed"):
            run_applescript("bad script")
