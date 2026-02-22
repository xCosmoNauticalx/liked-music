"""Tests for individual action modules."""

from unittest.mock import MagicMock, patch


class TestSyncAction:
    def test_sync_all_with_single_playlist(self):
        from likedmusic.playlist_config import PlaylistConfig

        playlists = [PlaylistConfig(name="Liked", source="liked")]
        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, "/tmp", 4)),
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            from likedmusic.actions.sync import _handle
            _handle(dry_run=True)
            mock_sync.assert_called_once_with(dry_run=True, sync_all=True)

    def test_sync_all_selected(self):
        from likedmusic.playlist_config import PlaylistConfig

        playlists = [
            PlaylistConfig(name="Liked", source="liked"),
            PlaylistConfig(name="EDM", source="EDM"),
        ]
        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, "/tmp", 4)),
            patch("questionary.select") as mock_select,
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_select.return_value.ask.return_value = "all"
            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)
            mock_sync.assert_called_once_with(dry_run=False, sync_all=True)

    def test_sync_specific_playlist(self):
        from likedmusic.playlist_config import PlaylistConfig

        playlists = [
            PlaylistConfig(name="Liked", source="liked"),
            PlaylistConfig(name="EDM", source="EDM"),
        ]
        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, "/tmp", 4)),
            patch("questionary.select") as mock_select,
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_select.return_value.ask.return_value = "EDM"
            from likedmusic.actions.sync import _handle
            _handle(dry_run=True)
            mock_sync.assert_called_once_with(dry_run=True, playlist_name="EDM")

    def test_sync_cancelled(self):
        from likedmusic.playlist_config import PlaylistConfig

        playlists = [
            PlaylistConfig(name="Liked", source="liked"),
            PlaylistConfig(name="EDM", source="EDM"),
        ]
        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, "/tmp", 4)),
            patch("questionary.select") as mock_select,
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_select.return_value.ask.return_value = None
            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)
            mock_sync.assert_not_called()


class TestConfigureAction:
    def test_calls_wizard(self):
        with patch("likedmusic.config_wizard.run_wizard") as mock_wizard:
            from likedmusic.actions.configure import _handle
            _handle(dry_run=False)
            mock_wizard.assert_called_once()


class TestSetupAuthAction:
    def test_calls_setup(self):
        with (
            patch("likedmusic.actions.setup_auth.ensure_dirs"),
            patch("likedmusic.ytmusic.setup_ytmusic_browser") as mock_setup,
        ):
            from likedmusic.actions.setup_auth import _handle
            _handle(dry_run=False)
            mock_setup.assert_called_once()


class TestStatusAction:
    def test_displays_table(self, tmp_path):
        from likedmusic.playlist_config import PlaylistConfig

        playlists = [PlaylistConfig(name="Liked", source="liked", apple_music_playlist="My Liked")]
        config_path = tmp_path / "config.yml"
        config_path.write_text("exists")

        with (
            patch("likedmusic.config.CONFIG_PATH", config_path),
            patch("likedmusic.playlist_config.load_config", return_value=(playlists, tmp_path, 4)),
            patch("likedmusic.state.load_playlist_state", return_value={
                "synced_songs": {"vid1": {}},
                "last_sync": "2026-01-01T00:00:00",
            }),
            patch("likedmusic.actions.status.console") as mock_console,
        ):
            from likedmusic.actions.status import _handle
            _handle(dry_run=False)
            assert mock_console.print.call_count >= 1

    def test_no_config_shows_message(self, tmp_path):
        config_path = tmp_path / "config.yml"
        with (
            patch("likedmusic.config.CONFIG_PATH", config_path),
            patch("likedmusic.actions.status.console") as mock_console,
        ):
            from likedmusic.actions.status import _handle
            _handle(dry_run=False)
            call_args = mock_console.print.call_args[0][0]
            assert "No configuration found" in call_args
