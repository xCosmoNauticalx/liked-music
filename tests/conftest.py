"""Shared fixtures for LikedMusic tests."""

from unittest.mock import patch

import pytest


@pytest.fixture()
def tmp_backup_dir(tmp_path):
    """Provide a temporary backup directory with Backup/ subfolder."""
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "Backup").mkdir()
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    with patch("likedmusic.config.DOWNLOADS_DIR", downloads_dir):
        yield {"backup_dir": backup_dir, "downloads_dir": downloads_dir}
