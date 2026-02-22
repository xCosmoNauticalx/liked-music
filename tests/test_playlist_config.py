"""Tests for likedmusic.playlist_config — YAML config loading and saving."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from likedmusic.playlist_config import PlaylistConfig, get_default_config, load_config, save_config


class TestGetDefaultConfig:
    def test_returns_liked_playlist(self):
        playlists, backup_dir, max_workers = get_default_config()
        assert len(playlists) == 1
        assert playlists[0].source == "liked"
        assert playlists[0].name == "YTM Liked Songs"
        assert playlists[0].apple_music_playlist == "YTM Liked Songs"

    def test_backup_dir_matches_hardcoded_default(self):
        _, backup_dir, _ = get_default_config()
        assert backup_dir == Path.home() / "Music" / "LikedMusic-Backup"

    def test_max_workers_default(self):
        _, _, max_workers = get_default_config()
        assert max_workers == 4


class TestLoadConfig:
    def test_no_file_returns_default(self, tmp_path):
        config_path = tmp_path / "config.yml"
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            playlists, backup_dir, max_workers = load_config()
        assert len(playlists) == 1
        assert playlists[0].source == "liked"
        assert max_workers == 4

    def test_parses_yaml(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(yaml.dump({
            "backup_dir": str(tmp_path / "backups"),
            "max_workers": 8,
            "playlists": [
                {
                    "name": "My Playlist",
                    "source": "liked",
                    "apple_music_playlist": "My Playlist",
                },
                {
                    "name": "EDM",
                    "source": "EDM Bangers",
                    "playlist_id": "PL123",
                    "apple_music_playlist": "EDM Mix",
                },
            ],
        }))
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            playlists, backup_dir, max_workers = load_config()
        assert len(playlists) == 2
        assert playlists[0].name == "My Playlist"
        assert playlists[1].source == "EDM Bangers"
        assert playlists[1].playlist_id == "PL123"
        assert backup_dir == tmp_path / "backups"
        assert max_workers == 8

    def test_expands_tilde_in_backup_dir(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(yaml.dump({
            "backup_dir": "~/Music/Backups",
            "playlists": [
                {"name": "Test", "source": "liked", "apple_music_playlist": "Test"},
            ],
        }))
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            _, backup_dir, _ = load_config()
        assert str(backup_dir).startswith(str(Path.home()))
        assert "~" not in str(backup_dir)

    def test_validates_required_fields(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(yaml.dump({
            "playlists": [{"name": "Missing Source"}],
        }))
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            with pytest.raises(ValueError, match="missing required fields"):
                load_config()

    def test_defaults_apple_music_playlist_to_name(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(yaml.dump({
            "playlists": [
                {"name": "My Songs", "source": "liked"},
            ],
        }))
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            playlists, _, _ = load_config()
        assert playlists[0].apple_music_playlist == "My Songs"

    def test_max_workers_defaults_when_missing(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(yaml.dump({
            "playlists": [
                {"name": "Test", "source": "liked"},
            ],
        }))
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            _, _, max_workers = load_config()
        assert max_workers == 4


class TestSaveConfig:
    def test_caches_playlist_id(self, tmp_path):
        config_path = tmp_path / "config.yml"
        playlists = [
            PlaylistConfig(name="Test", source="My Playlist", playlist_id="PL999", apple_music_playlist="Test"),
        ]
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            save_config(playlists, tmp_path / "backups")

        raw = yaml.safe_load(config_path.read_text())
        assert raw["playlists"][0]["playlist_id"] == "PL999"

    def test_roundtrip(self, tmp_path):
        config_path = tmp_path / "config.yml"
        playlists = [
            PlaylistConfig(name="Liked", source="liked", apple_music_playlist="Liked"),
            PlaylistConfig(name="EDM", source="EDM Mix", playlist_id="PL1", apple_music_playlist="EDM"),
        ]
        backup_dir = tmp_path / "backups"
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            save_config(playlists, backup_dir, max_workers=6)
            loaded_playlists, loaded_dir, loaded_workers = load_config()

        assert len(loaded_playlists) == 2
        assert loaded_playlists[1].playlist_id == "PL1"
        assert loaded_dir == backup_dir
        assert loaded_workers == 6

    def test_max_workers_roundtrip(self, tmp_path):
        config_path = tmp_path / "config.yml"
        playlists = [
            PlaylistConfig(name="Test", source="liked", apple_music_playlist="Test"),
        ]
        with patch("likedmusic.playlist_config.config.CONFIG_PATH", config_path):
            save_config(playlists, tmp_path / "backups", max_workers=12)
            _, _, max_workers = load_config()
        assert max_workers == 12
