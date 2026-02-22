"""Tests for likedmusic.cli — interactive CLI main loop."""

from unittest.mock import MagicMock, patch

from likedmusic.cli import _auto_setup, _parse_args, main


class TestParseArgs:
    def test_dry_run_flag(self):
        with patch("sys.argv", ["likedmusic", "--dry-run"]):
            assert _parse_args() is True

    def test_no_args_defaults_no_dry_run(self):
        with patch("sys.argv", ["likedmusic"]):
            assert _parse_args() is False


class TestAutoSetup:
    def test_skips_when_config_exists(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text("playlists: []")
        with patch("likedmusic.cli.CONFIG_PATH", config_path):
            with patch("likedmusic.cli.console") as mock_console:
                _auto_setup()
                mock_console.print.assert_not_called()

    def test_runs_wizard_when_no_config(self, tmp_path):
        config_path = tmp_path / "config.yml"
        with (
            patch("likedmusic.cli.CONFIG_PATH", config_path),
            patch("likedmusic.config_wizard.run_wizard") as mock_wizard,
        ):
            _auto_setup()
            mock_wizard.assert_called_once()


class TestMainLoop:
    def test_quit_exits_cleanly(self):
        with (
            patch("sys.argv", ["likedmusic"]),
            patch("likedmusic.cli.ensure_dirs"),
            patch("likedmusic.cli._auto_setup"),
            patch("likedmusic.cli.console"),
            patch("likedmusic.cli.get_actions", return_value=[]),
            patch("questionary.select") as mock_select,
        ):
            mock_select.return_value.ask.return_value = None
            main()
            mock_select.assert_called_once()

    def test_action_handler_called_with_dry_run(self):
        mock_handler = MagicMock()
        mock_action = MagicMock()
        mock_action.name = "Test"
        mock_action.description = "desc"
        mock_action.handler = mock_handler

        with (
            patch("sys.argv", ["likedmusic", "--dry-run"]),
            patch("likedmusic.cli.ensure_dirs"),
            patch("likedmusic.cli._auto_setup"),
            patch("likedmusic.cli.console"),
            patch("likedmusic.cli.get_actions", return_value=[mock_action]),
            patch("questionary.select") as mock_select,
            patch("questionary.Choice", side_effect=lambda **kwargs: kwargs.get("value")),
        ):
            mock_select.return_value.ask.side_effect = [mock_action, None]
            main()
            mock_handler.assert_called_once_with(True)

    def test_keyboard_interrupt_returns_to_menu(self):
        mock_action = MagicMock()
        mock_action.name = "Test"
        mock_action.description = "desc"
        mock_action.handler.side_effect = KeyboardInterrupt

        with (
            patch("sys.argv", ["likedmusic"]),
            patch("likedmusic.cli.ensure_dirs"),
            patch("likedmusic.cli._auto_setup"),
            patch("likedmusic.cli.console"),
            patch("likedmusic.cli.get_actions", return_value=[mock_action]),
            patch("questionary.select") as mock_select,
            patch("questionary.Choice", side_effect=lambda **kwargs: kwargs.get("value")),
        ):
            # First call returns the action (which raises), second call returns Quit
            mock_select.return_value.ask.side_effect = [mock_action, None]
            main()
            assert mock_select.return_value.ask.call_count == 2

    def test_exception_returns_to_menu(self):
        mock_action = MagicMock()
        mock_action.name = "Test"
        mock_action.description = "desc"
        mock_action.handler.side_effect = RuntimeError("boom")

        with (
            patch("sys.argv", ["likedmusic"]),
            patch("likedmusic.cli.ensure_dirs"),
            patch("likedmusic.cli._auto_setup"),
            patch("likedmusic.cli.console"),
            patch("likedmusic.cli.get_actions", return_value=[mock_action]),
            patch("questionary.select") as mock_select,
            patch("questionary.Choice", side_effect=lambda **kwargs: kwargs.get("value")),
        ):
            mock_select.return_value.ask.side_effect = [mock_action, None]
            main()
            assert mock_select.return_value.ask.call_count == 2
