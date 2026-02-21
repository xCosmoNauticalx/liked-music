"""Tests for likedmusic.downloader — download_song and download_songs."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from likedmusic.downloader import download_song, download_songs


class TestDownloadSong:
    @patch("likedmusic.downloader.yt_dlp.YoutubeDL")
    def test_successful_download(self, mock_ytdl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ytdl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ytdl_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = download_song("abc123", tmp_path)
        assert result == tmp_path / "abc123.m4a"
        mock_ydl.download.assert_called_once()

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
    @patch("likedmusic.downloader.download_song")
    def test_batch_download(self, mock_dl, tmp_path):
        songs = [
            {"videoId": "a", "title": "Song A"},
            {"videoId": "b", "title": "Song B"},
        ]
        mock_dl.side_effect = lambda vid, out_dir, **kw: out_dir / f"{vid}.m4a"

        results = download_songs(songs, tmp_path, max_workers=2)
        assert "a" in results
        assert "b" in results
        assert mock_dl.call_count == 2
