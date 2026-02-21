"""Tests for likedmusic.metadata — embed_metadata."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from likedmusic.metadata import embed_metadata


class TestEmbedMetadata:
    @patch("likedmusic.metadata.MP4")
    @patch("likedmusic.metadata.requests.get")
    def test_with_thumbnail(self, mock_get, mock_mp4_cls):
        mock_resp = MagicMock()
        mock_resp.content = b"fake image data"
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_get.return_value = mock_resp

        mock_audio = MagicMock()
        mock_mp4_cls.return_value = mock_audio

        embed_metadata(Path("/fake/song.m4a"), "Title", "Artist", "Album", "http://img.com/art.jpg")

        mock_get.assert_called_once_with("http://img.com/art.jpg", timeout=10)
        mock_audio.save.assert_called_once()
        assert mock_audio.__setitem__.call_count >= 3  # title, artist, album + covr

    @patch("likedmusic.metadata.MP4")
    def test_without_thumbnail(self, mock_mp4_cls):
        mock_audio = MagicMock()
        mock_mp4_cls.return_value = mock_audio

        embed_metadata(Path("/fake/song.m4a"), "Title", "Artist", None, None)

        mock_audio.save.assert_called_once()
        # Should set title and artist
        calls = {call[0][0] for call in mock_audio.__setitem__.call_args_list}
        assert "\xa9nam" in calls
        assert "\xa9ART" in calls

    @patch("likedmusic.metadata.MP4")
    @patch("likedmusic.metadata.requests.get")
    def test_failed_thumbnail_warns_but_does_not_raise(self, mock_get, mock_mp4_cls):
        mock_get.side_effect = Exception("network error")
        mock_audio = MagicMock()
        mock_mp4_cls.return_value = mock_audio

        # Should not raise
        embed_metadata(Path("/fake/song.m4a"), "Title", "Artist", None, "http://img.com/art.jpg")
        mock_audio.save.assert_called_once()
