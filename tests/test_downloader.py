"""Tests for likedmusic.downloader — download_song and download_songs."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from likedmusic.downloader import _write_cookie_file, download_song, download_songs


class TestWriteCookieFile:
    def test_writes_netscape_format(self, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({
            "cookie": "SID=abc123; HSID=def456; SSID=ghi789",
        }))
        cookie_dir = tmp_path / "data"
        cookie_dir.mkdir()

        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json), \
             patch("likedmusic.downloader.DATA_DIR", cookie_dir):
            result = _write_cookie_file()

        assert result is not None
        content = result.read_text()
        assert "# Netscape HTTP Cookie File" in content
        assert ".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tabc123" in content
        assert ".youtube.com\tTRUE\t/\tTRUE\t0\tHSID\tdef456" in content
        assert ".youtube.com\tTRUE\t/\tTRUE\t0\tSSID\tghi789" in content

    def test_returns_none_when_no_auth_file(self, tmp_path):
        missing = tmp_path / "browser.json"

        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", missing):
            result = _write_cookie_file()

        assert result is None

    def test_returns_none_when_no_cookie_header(self, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({"user-agent": "test"}))

        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json):
            result = _write_cookie_file()

        assert result is None

    def test_handles_cookie_values_with_equals(self, tmp_path):
        browser_json = tmp_path / "browser.json"
        browser_json.write_text(json.dumps({
            "cookie": "TOKEN=abc=def=ghi",
        }))
        cookie_dir = tmp_path / "data"
        cookie_dir.mkdir()

        with patch("likedmusic.downloader.BROWSER_AUTH_PATH", browser_json), \
             patch("likedmusic.downloader.DATA_DIR", cookie_dir):
            result = _write_cookie_file()

        content = result.read_text()
        assert ".youtube.com\tTRUE\t/\tTRUE\t0\tTOKEN\tabc=def=ghi" in content


class TestDownloadSong:
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_successful_download(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = download_song("abc123", tmp_path)
        assert result == tmp_path / "abc123.m4a"
        mock_ydl.download.assert_called_once()

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_cookiefile_passed_to_opts(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        cookie_path = tmp_path / "cookies.txt"
        cookie_path.touch()
        download_song("abc123", tmp_path, cookiefile=cookie_path)

        opts = mock_ytdl_cls.call_args[0][0]
        assert opts["cookiefile"] == str(cookie_path)

    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_no_cookiefile_when_none(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        download_song("abc123", tmp_path, cookiefile=None)

        opts = mock_ytdl_cls.call_args[0][0]
        assert "cookiefile" not in opts

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
    @patch("likedmusic.downloader._write_cookie_file", return_value=None)
    @patch("likedmusic.downloader.download_song")
    def test_batch_download(self, mock_dl, mock_cookie, tmp_path):
        songs = [
            {"videoId": "a", "title": "Song A"},
            {"videoId": "b", "title": "Song B"},
        ]
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        results = download_songs(songs, tmp_path, max_workers=2)
        assert "a" in results
        assert "b" in results
        assert mock_dl.call_count == 2

    @patch("likedmusic.downloader._write_cookie_file")
    @patch("likedmusic.downloader.download_song")
    def test_batch_passes_cookiefile(self, mock_dl, mock_cookie, tmp_path):
        cookie_path = tmp_path / "cookies.txt"
        mock_cookie.return_value = cookie_path
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        songs = [{"videoId": "a", "title": "Song A"}]
        download_songs(songs, tmp_path)

        mock_dl.assert_called_once()
        _, kwargs = mock_dl.call_args
        assert kwargs["cookiefile"] == cookie_path
