"""Tests for likedmusic.state — load_state and save_state (file I/O)."""

import json
from unittest.mock import patch

import pytest

from likedmusic.state import load_state, save_state


class TestLoadState:
    def test_file_exists_valid_json(self, tmp_path):
        state_path = tmp_path / "sync_state.json"
        data = {"synced_songs": {"vid1": {}}, "last_sync": None, "playlist_order": []}
        state_path.write_text(json.dumps(data))

        with patch("likedmusic.state.config.STATE_PATH", state_path):
            result = load_state()

        assert result == data

    def test_file_missing_returns_default(self, tmp_path):
        state_path = tmp_path / "nonexistent.json"
        with patch("likedmusic.state.config.STATE_PATH", state_path):
            result = load_state()

        assert result == {
            "synced_songs": {},
            "last_sync": None,
            "playlist_order": [],
        }

    def test_malformed_json_raises(self, tmp_path):
        state_path = tmp_path / "sync_state.json"
        state_path.write_text("{not valid json")

        with patch("likedmusic.state.config.STATE_PATH", state_path):
            with pytest.raises(json.JSONDecodeError):
                load_state()


class TestSaveState:
    def test_atomic_write(self, tmp_path):
        state_path = tmp_path / "sync_state.json"
        data = {"synced_songs": {}, "playlist_order": []}

        with patch("likedmusic.state.config.STATE_PATH", state_path):
            save_state(data)

        assert state_path.exists()
        saved = json.loads(state_path.read_text())
        assert "last_sync" in saved
        assert saved["synced_songs"] == {}

    def test_overwrites_existing(self, tmp_path):
        state_path = tmp_path / "sync_state.json"
        state_path.write_text(json.dumps({"old": True}))

        data = {"synced_songs": {"new": {}}, "playlist_order": []}
        with patch("likedmusic.state.config.STATE_PATH", state_path):
            save_state(data)

        saved = json.loads(state_path.read_text())
        assert "new" in saved["synced_songs"]
