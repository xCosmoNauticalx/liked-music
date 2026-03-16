"""Tests for likedmusic.downloader — download_song and download_songs."""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from likedmusic.downloader import (
    _check_ffmpeg,
    _extract_cookies,
    _find_js_runtime,
    download_song,
    download_songs,
)


class TestCheckFfmpeg:
    @patch("likedmusic.downloader.shutil.which", side_effect=lambda cmd: {
        "ffmpeg": "/usr/local/bin/ffmpeg",
        "ffprobe": "/usr/local/bin/ffprobe",
    }.get(cmd))
    def test_passes_when_both_on_path(self, mock_which):
        result = _check_ffmpeg()
        assert result is None

    @patch("likedmusic.downloader.shutil.which", return_value=None)
    def test_falls_back_to_static_ffmpeg(self, mock_which):
        mock_run = MagicMock()
        mock_run.get_or_fetch_platform_executables_else_raise.return_value = (
            "/cache/bin/ffmpeg", "/cache/bin/ffprobe"
        )
        mock_static = MagicMock()
        mock_static.run = mock_run
        with patch.dict(sys.modules, {"static_ffmpeg": mock_static, "static_ffmpeg.run": mock_run}):
            result = _check_ffmpeg()
        assert result == "/cache/bin"

    @patch.dict(sys.modules, {"static_ffmpeg": None, "static_ffmpeg.run": None})
    @patch("likedmusic.downloader.shutil.which", side_effect=lambda cmd: {
        "ffmpeg": "/usr/local/bin/ffmpeg",
    }.get(cmd))
    def test_ffmpeg_only_warns(self, mock_which):
        result = _check_ffmpeg()
        assert result is None

    @patch.dict(sys.modules, {"static_ffmpeg": None, "static_ffmpeg.run": None})
    @patch("likedmusic.downloader.shutil.which", return_value=None)
    def test_raises_when_nothing_available(self, mock_which):
        with pytest.raises(RuntimeError, match="ffmpeg is required"):
            _check_ffmpeg()


class TestFindJsRuntime:
    @patch("likedmusic.downloader.shutil.which", side_effect=lambda r: "/usr/local/bin/node" if r == "node" else None)
    def test_finds_first_available(self, mock_which):
        result = _find_js_runtime()
        assert result == {"node": {}}

    @patch("likedmusic.downloader.shutil.which", return_value=None)
    def test_returns_empty_when_none(self, mock_which):
        result = _find_js_runtime()
        assert result == {}


class TestExtractCookies:
    def test_returns_none_when_no_auth_file(self, tmp_path):
        missing = tmp_path / "browser.json"
        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", missing):
            result = _extract_cookies()
        assert result is None

    def test_returns_none_when_invalid_json(self, tmp_path):
        bad_json = tmp_path / "browser.json"
        bad_json.write_text("not json")
        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", bad_json):
            result = _extract_cookies()
        assert result is None

    def test_returns_none_when_no_browser_key(self, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({"cookie": "SID=abc"}))
        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json):
            result = _extract_cookies()
        assert result is None

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_extracts_cookies_successfully(self, mock_ytdl_cls, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({"_browser": "chrome"}))
        cookie_file = tmp_path / "cookies.txt"

        mock_ydl = MagicMock()
        type(mock_ydl).cookiejar = PropertyMock(return_value=MagicMock())
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json),
            patch("likedmusic.downloader._COOKIE_FILE", cookie_file),
            patch("likedmusic.downloader._find_js_runtime", return_value={"node": {}}),
        ):
            # Simulate yt-dlp creating the cookie file
            cookie_file.write_text("# Netscape cookies")
            result = _extract_cookies()

        assert result == cookie_file
        opts = mock_ytdl_cls.call_args[0][0]
        assert opts["cookiesfrombrowser"] == ("chrome",)
        assert opts["cookiefile"] == str(cookie_file)
        assert opts["js_runtimes"] == {"node": {}}

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_returns_none_when_extraction_fails(self, mock_ytdl_cls, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({"_browser": "chrome"}))

        mock_ytdl_cls.return_value.__enter__ = MagicMock(side_effect=Exception("Keychain denied"))

        with (
            patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json),
            patch("likedmusic.downloader._find_js_runtime", return_value={}),
        ):
            result = _extract_cookies()

        assert result is None

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_returns_none_when_cookie_file_not_created(self, mock_ytdl_cls, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({"_browser": "chrome"}))
        cookie_file = tmp_path / "cookies.txt"  # not created

        mock_ydl = MagicMock()
        type(mock_ydl).cookiejar = PropertyMock(return_value=MagicMock())
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json),
            patch("likedmusic.downloader._COOKIE_FILE", cookie_file),
            patch("likedmusic.downloader._find_js_runtime", return_value={}),
        ):
            result = _extract_cookies()

        assert result is None


class TestDownloadSong:
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_successful_download(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = download_song("abc123", tmp_path)
        assert result == tmp_path / "abc123.m4a"
        mock_ydl.download.assert_called_once()

    @patch("likedmusic.downloader._find_js_runtime", return_value={})
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_cookiefile_passed_to_opts(self, mock_ytdl_cls, mock_js, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        cookie_path = tmp_path / "cookies.txt"
        download_song("abc123", tmp_path, cookiefile=cookie_path)

        opts = mock_ytdl_cls.call_args[0][0]
        assert opts["cookiefile"] == str(cookie_path)

    @patch("likedmusic.downloader._find_js_runtime", return_value={})
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_no_cookiefile_when_none(self, mock_ytdl_cls, mock_js, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        download_song("abc123", tmp_path, cookiefile=None)

        opts = mock_ytdl_cls.call_args[0][0]
        assert "cookiefile" not in opts

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_ffmpeg_location_passed_to_opts(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        download_song("abc123", tmp_path, ffmpeg_location="/bundled")

        opts = mock_ytdl_cls.call_args[0][0]
        assert opts["ffmpeg_location"] == "/bundled"

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_no_ffmpeg_location_when_none(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        download_song("abc123", tmp_path, ffmpeg_location=None)

        opts = mock_ytdl_cls.call_args[0][0]
        assert "ffmpeg_location" not in opts

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_postprocessor_in_opts(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        download_song("abc123", tmp_path)

        opts = mock_ytdl_cls.call_args[0][0]
        assert opts["format"] == "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        assert opts["extractor_args"] == {"youtube": {"player_js_variant": ["main"]}}
        assert any(pp["key"] == "FFmpegExtractAudio" for pp in opts["postprocessors"])

    @patch("likedmusic.downloader.time.sleep")
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_retry_on_failure(self, mock_ytdl_cls, mock_sleep, tmp_path):
        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = [Exception("fail"), None]
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = download_song("abc123", tmp_path, max_retries=2)
        assert result == tmp_path / "abc123.m4a"
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    @patch("likedmusic.downloader.time.sleep")
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_max_retries_raises(self, mock_ytdl_cls, mock_sleep, tmp_path):
        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = Exception("persistent failure")
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(RuntimeError, match="Failed to download"):
            download_song("abc123", tmp_path, max_retries=3)

    def test_file_already_exists(self, tmp_path):
        existing = tmp_path / "abc123.m4a"
        existing.touch()
        result = download_song("abc123", tmp_path)
        assert result == existing


class TestDownloadSongs:
    @patch("likedmusic.downloader._setup_logging")
    @patch("likedmusic.downloader._extract_cookies", return_value=None)
    @patch("likedmusic.downloader._check_ffmpeg", return_value=None)
    @patch("likedmusic.downloader.download_song")
    def test_batch_download(self, mock_dl, mock_ffmpeg, mock_cookies, mock_logging, tmp_path):
        songs = [
            {"videoId": "a", "title": "Song A"},
            {"videoId": "b", "title": "Song B"},
        ]
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        results = download_songs(songs, tmp_path, max_workers=2)
        assert "a" in results
        assert "b" in results
        assert mock_dl.call_count == 2

    @patch("likedmusic.downloader._setup_logging")
    @patch("likedmusic.downloader._extract_cookies")
    @patch("likedmusic.downloader._check_ffmpeg", return_value=None)
    @patch("likedmusic.downloader.download_song")
    def test_batch_passes_cookiefile(self, mock_dl, mock_ffmpeg, mock_cookies, mock_logging, tmp_path):
        cookie_path = tmp_path / "cookies.txt"
        cookie_path.write_text("# cookies")
        mock_cookies.return_value = cookie_path
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        songs = [{"videoId": "a", "title": "Song A"}]
        download_songs(songs, tmp_path)

        mock_dl.assert_called_once()
        _, kwargs = mock_dl.call_args
        assert kwargs["cookiefile"] == cookie_path

    @patch("likedmusic.downloader._setup_logging")
    @patch("likedmusic.downloader._extract_cookies")
    @patch("likedmusic.downloader._check_ffmpeg", return_value=None)
    @patch("likedmusic.downloader.download_song")
    def test_cookie_file_cleaned_up(self, mock_dl, mock_ffmpeg, mock_cookies, mock_logging, tmp_path):
        cookie_path = tmp_path / "cookies.txt"
        cookie_path.write_text("# cookies")
        mock_cookies.return_value = cookie_path
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        songs = [{"videoId": "a", "title": "Song A"}]
        download_songs(songs, tmp_path)

        assert not cookie_path.exists()

    @patch("likedmusic.downloader._setup_logging")
    @patch("likedmusic.downloader._extract_cookies", return_value=None)
    @patch("likedmusic.downloader._check_ffmpeg", return_value="/bundled/bin")
    @patch("likedmusic.downloader.download_song")
    def test_batch_passes_ffmpeg_location(self, mock_dl, mock_ffmpeg, mock_cookies, mock_logging, tmp_path):
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        songs = [{"videoId": "a", "title": "Song A"}]
        download_songs(songs, tmp_path)

        mock_dl.assert_called_once()
        _, kwargs = mock_dl.call_args
        assert kwargs["ffmpeg_location"] == "/bundled/bin"

    @patch("likedmusic.downloader._setup_logging")
    @patch("likedmusic.downloader._extract_cookies", return_value=None)
    @patch("likedmusic.downloader._check_ffmpeg", return_value=None)
    @patch("likedmusic.downloader.download_song")
    def test_batch_passes_dashboard_callbacks(self, mock_dl, mock_ffmpeg, mock_cookies, mock_logging, tmp_path):
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"
        dashboard = MagicMock()

        songs = [{"videoId": "a", "title": "Song A"}]
        download_songs(songs, tmp_path, dashboard=dashboard)

        dashboard.mark_active.assert_called_once_with("Song A")
        dashboard.mark_completed.assert_called_once_with("Song A")
