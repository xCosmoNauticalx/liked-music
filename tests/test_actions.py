"""Tests for individual action modules."""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSyncAction:
    """Tests for the redesigned sync action with pre-fetch and checkbox UI."""

    def _make_playlists(self):
        from likedmusic.playlist_config import PlaylistConfig
        return [
            PlaylistConfig(name="Liked", source="liked", apple_music_playlist="Liked"),
            PlaylistConfig(name="EDM", source="EDM", apple_music_playlist="EDM"),
        ]

    def _make_stats(self, playlists, new_counts=None, pending_counts=None):
        new_counts = new_counts or [0, 0]
        pending_counts = pending_counts or [0, 0]
        return [
            {
                "playlist": pl,
                "new_count": nc,
                "pending_count": pc,
                "last_sync": "just now",
                "tracks": [],
            }
            for pl, nc, pc in zip(playlists, new_counts, pending_counts)
        ]

    def test_no_playlists_returns_early(self):
        with (
            patch("likedmusic.actions.sync.load_config", return_value=([], "/tmp", 4)),
            patch("likedmusic.actions.sync._fetch_all_stats") as mock_fetch,
        ):
            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)
            mock_fetch.assert_not_called()

    def test_checkbox_none_returns_early(self):
        playlists = self._make_playlists()
        stats = self._make_stats(playlists, new_counts=[3, 0])

        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, Path("/tmp"), 4)),
            patch("likedmusic.actions.sync._fetch_all_stats", return_value=stats),
            patch("likedmusic.actions.sync.questionary") as mock_q,
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_q.checkbox.return_value.ask.return_value = None
            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)
            mock_sync.assert_not_called()

    def test_nothing_selected_returns_early(self):
        playlists = self._make_playlists()
        stats = self._make_stats(playlists)

        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, Path("/tmp"), 4)),
            patch("likedmusic.actions.sync._fetch_all_stats", return_value=stats),
            patch("likedmusic.actions.sync.questionary") as mock_q,
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_q.checkbox.return_value.ask.return_value = []
            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)
            mock_sync.assert_not_called()

    def test_sync_selected_playlist(self):
        playlists = self._make_playlists()
        stats = self._make_stats(playlists, new_counts=[5, 0])

        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, Path("/tmp"), 4)),
            patch("likedmusic.actions.sync._fetch_all_stats", return_value=stats),
            patch("likedmusic.actions.sync.questionary") as mock_q,
            patch("likedmusic.actions.sync.prompt_max_workers", return_value=4),
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_q.checkbox.return_value.ask.return_value = ["Liked"]
            mock_q.select.return_value.ask.return_value = "Download + Apple Music"

            from likedmusic.actions.sync import _handle
            _handle(dry_run=True)

            mock_sync.assert_called_once_with(
                max_workers=4,
                dry_run=True,
                playlist_name="Liked",
                download_only=False,
            )

    def test_sync_download_only_mode(self):
        playlists = self._make_playlists()
        stats = self._make_stats(playlists, new_counts=[2, 0])

        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, Path("/tmp"), 4)),
            patch("likedmusic.actions.sync._fetch_all_stats", return_value=stats),
            patch("likedmusic.actions.sync.questionary") as mock_q,
            patch("likedmusic.actions.sync.prompt_max_workers", return_value=2),
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_q.checkbox.return_value.ask.return_value = ["Liked"]
            mock_q.select.return_value.ask.return_value = "Download only (skip Apple Music)"

            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)

            mock_sync.assert_called_once_with(
                max_workers=2,
                dry_run=False,
                playlist_name="Liked",
                download_only=True,
            )

    def test_add_pending_selected(self):
        playlists = self._make_playlists()
        stats = self._make_stats(playlists, pending_counts=[3, 0])

        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, Path("/tmp"), 4)),
            patch("likedmusic.actions.sync._fetch_all_stats", return_value=stats),
            patch("likedmusic.actions.sync.questionary") as mock_q,
            patch("likedmusic.sync_engine.add_pending_to_apple_music") as mock_pending,
        ):
            mock_q.checkbox.return_value.ask.return_value = ["__add_pending__"]

            from likedmusic.actions.sync import _handle
            _handle(dry_run=False)

            mock_pending.assert_called_once_with(playlists[0], Path("/tmp"))

    def test_workers_none_returns_early(self):
        playlists = self._make_playlists()
        stats = self._make_stats(playlists, new_counts=[1, 0])

        with (
            patch("likedmusic.actions.sync.load_config", return_value=(playlists, Path("/tmp"), 4)),
            patch("likedmusic.actions.sync._fetch_all_stats", return_value=stats),
            patch("likedmusic.actions.sync.questionary") as mock_q,
            patch("likedmusic.actions.sync.prompt_max_workers", return_value=None),
            patch("likedmusic.sync_engine.run_sync") as mock_sync,
        ):
            mock_q.checkbox.return_value.ask.return_value = ["Liked"]

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
