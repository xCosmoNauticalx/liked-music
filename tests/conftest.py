"""Shared fixtures for LikedMusic tests."""

from unittest.mock import patch

import pytest


@pytest.fixture()
def tmp_state_dir(tmp_path):
    """Provide temporary directories for state and downloads, patching config paths."""
    state_path = tmp_path / "sync_state.json"
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    with (
        patch("likedmusic.config.STATE_PATH", state_path),
        patch("likedmusic.state.STATE_PATH", state_path),
        patch("likedmusic.config.DOWNLOADS_DIR", downloads_dir),
    ):
        yield {"state_path": state_path, "downloads_dir": downloads_dir}
