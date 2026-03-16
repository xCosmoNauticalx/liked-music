"""Tests for likedmusic.config — paths and ensure_dirs."""

from unittest.mock import patch, MagicMock


def test_ensure_dirs_creates_directories():
    from likedmusic.config import ensure_dirs

    mock_dirs = {}
    for name in ["DATA_DIR", "DOWNLOADS_DIR", "BACKUP_DIR"]:
        m = MagicMock()
        mock_dirs[name] = m

    backup_mock = mock_dirs["BACKUP_DIR"]
    subdir_mock = MagicMock()
    backup_mock.__truediv__ = MagicMock(return_value=subdir_mock)

    with (
        patch("likedmusic.config.DATA_DIR", mock_dirs["DATA_DIR"]),
        patch("likedmusic.config.DOWNLOADS_DIR", mock_dirs["DOWNLOADS_DIR"]),
        patch("likedmusic.config.BACKUP_DIR", backup_mock),
    ):
        ensure_dirs()

    mock_dirs["DATA_DIR"].mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_dirs["DOWNLOADS_DIR"].mkdir.assert_called_once_with(parents=True, exist_ok=True)
    backup_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    subdir_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)
