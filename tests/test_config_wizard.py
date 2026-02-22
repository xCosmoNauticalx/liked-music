"""Tests for likedmusic.config_wizard — interactive config wizard."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from likedmusic.config_wizard import (
    _ensure_auth,
    _prompt_playlist_selection,
    run_wizard,
)
from likedmusic.playlist_config import PlaylistConfig


class TestEnsureAuth:
    def test_returns_true_when_browser_json_exists(self, tmp_path):
        browser_path = tmp_path / "browser.json"
        browser_path.write_text("{}")
        with patch("likedmusic.config_wizard.BROWSER_AUTH_PATH", browser_path):
            assert _ensure_auth() is True

    def test_returns_false_when_missing_and_user_declines(self, tmp_path):
        browser_path = tmp_path / "browser.json"
        with (
            patch("likedmusic.config_wizard.BROWSER_AUTH_PATH", browser_path),
            patch("likedmusic.config_wizard.questionary") as mock_q,
        ):
            mock_q.confirm.return_value.ask.return_value = False
            assert _ensure_auth() is False

    def test_triggers_setup_when_missing_and_user_accepts(self, tmp_path):
        browser_path = tmp_path / "browser.json"

        def fake_setup():
            browser_path.write_text("{}")

        with (
            patch("likedmusic.config_wizard.BROWSER_AUTH_PATH", browser_path),
            patch("likedmusic.config_wizard.questionary") as mock_q,
            patch("likedmusic.ytmusic.setup_ytmusic_browser", side_effect=fake_setup),
        ):
            mock_q.confirm.return_value.ask.return_value = True
            assert _ensure_auth() is True


class TestPromptPlaylistSelection:
    def test_returns_selected_playlists(self):
        library = [
            {"title": "EDM Bangers", "playlistId": "PL_edm"},
            {"title": "Chill Vibes", "playlistId": "PL_chill"},
        ]
        mock_result = [
            {"title": "EDM Bangers", "playlistId": "PL_edm", "source": "EDM Bangers"},
        ]
        with patch("likedmusic.config_wizard.questionary") as mock_q:
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs.get("value"))
            mock_q.checkbox.return_value.ask.return_value = mock_result
            result = _prompt_playlist_selection(library)

        assert len(result) == 1
        assert result[0]["title"] == "EDM Bangers"

    def test_empty_library_shows_empty_choices(self):
        with patch("likedmusic.config_wizard.questionary") as mock_q:
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs.get("value"))
            mock_q.checkbox.return_value.ask.return_value = []
            _prompt_playlist_selection([])

        mock_q.checkbox.assert_called_once()


class TestRunWizard:
    def test_end_to_end_saves_config(self, tmp_path):
        browser_path = tmp_path / "browser.json"
        browser_path.write_text("{}")
        liked = {"title": "YTM Liked Songs", "playlistId": None, "source": "liked"}
        edm = {"title": "EDM Bangers", "playlistId": "PL_edm", "source": "EDM Bangers"}

        with (
            patch("likedmusic.config_wizard.BROWSER_AUTH_PATH", browser_path),
            patch("likedmusic.config_wizard.questionary") as mock_q,
            patch("likedmusic.config_wizard._fetch_library_playlists") as mock_fetch,
            patch("likedmusic.config_wizard.save_config") as mock_save,
        ):
            mock_fetch.return_value = [{"title": "EDM Bangers", "playlistId": "PL_edm"}]

            # Mock questionary calls in order:
            # 1. _prompt_max_workers -> text("4")
            # 2. _prompt_playlist_selection -> checkbox([liked, edm])
            # 3. _prompt_apple_music_names -> text("YTM Liked Songs"), text("EDM Bangers")
            # 4. _show_summary -> confirm(True)
            mock_q.Choice = MagicMock(side_effect=lambda **kwargs: kwargs.get("value"))
            mock_q.text.return_value.ask.side_effect = ["4", "YTM Liked Songs", "EDM Bangers"]
            mock_q.checkbox.return_value.ask.return_value = [liked, edm]
            mock_q.confirm.return_value.ask.return_value = True

            run_wizard()

            mock_save.assert_called_once()
            args = mock_save.call_args
            saved_playlists = args[0][0]
            assert len(saved_playlists) == 2
            assert saved_playlists[0].source == "liked"
            assert saved_playlists[1].playlist_id == "PL_edm"
            assert args[0][2] == 4

    def test_aborts_on_ctrl_c(self, tmp_path):
        browser_path = tmp_path / "browser.json"
        browser_path.write_text("{}")

        with (
            patch("likedmusic.config_wizard.BROWSER_AUTH_PATH", browser_path),
            patch("likedmusic.config_wizard.questionary") as mock_q,
        ):
            # Simulate Ctrl+C on first prompt (max workers)
            mock_q.text.return_value.ask.return_value = None

            with pytest.raises(SystemExit):
                run_wizard()

    def test_aborts_when_auth_fails(self, tmp_path):
        browser_path = tmp_path / "browser.json"

        with (
            patch("likedmusic.config_wizard.BROWSER_AUTH_PATH", browser_path),
            patch("likedmusic.config_wizard.questionary") as mock_q,
            patch("likedmusic.config_wizard.save_config") as mock_save,
        ):
            mock_q.confirm.return_value.ask.return_value = False
            run_wizard()
            mock_save.assert_not_called()
