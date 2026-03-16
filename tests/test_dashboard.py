"""Tests for likedmusic.dashboard — DownloadDashboard."""

from io import StringIO

from rich.console import Console

from likedmusic.dashboard import DownloadDashboard


class TestDownloadDashboard:
    def test_mark_active_adds_to_list(self):
        dash = DownloadDashboard(total=3)
        dash.mark_active("Song A")
        assert "Song A" in dash.active

    def test_mark_completed_moves_from_active(self):
        dash = DownloadDashboard(total=3)
        dash.mark_active("Song A")
        dash.mark_completed("Song A")
        assert "Song A" not in dash.active
        assert "Song A" in dash.completed

    def test_mark_error_moves_from_active(self):
        dash = DownloadDashboard(total=3)
        dash.mark_active("Song A")
        dash.mark_error("Song A", "timeout")
        assert "Song A" not in dash.active
        assert ("Song A", "timeout") in dash.errors

    def test_errors_count_toward_progress(self):
        dash = DownloadDashboard(total=3)
        dash.mark_active("Song A")
        dash.mark_error("Song A", "fail")
        dash.mark_active("Song B")
        dash.mark_completed("Song B")
        # 1 error + 1 completed = 2 done
        rendered = dash._render()
        output = StringIO()
        console = Console(file=output, color_system=None)
        console.print(rendered)
        assert "2/3" in output.getvalue()

    def test_render_shows_active_in_output(self):
        dash = DownloadDashboard(total=2)
        dash.mark_active("Neon Lights")
        rendered = dash._render()
        output = StringIO()
        console = Console(file=output, color_system=None)
        console.print(rendered)
        assert "Downloading: Neon Lights" in output.getvalue()

    def test_render_shows_error_message(self):
        dash = DownloadDashboard(total=1)
        dash.mark_active("Bad Track")
        dash.mark_error("Bad Track", "format not available")
        rendered = dash._render()
        output = StringIO()
        console = Console(file=output, color_system=None)
        console.print(rendered)
        text = output.getvalue()
        assert "Bad Track" in text
        assert "format not available" in text

    def test_render_shows_completed(self):
        dash = DownloadDashboard(total=1)
        dash.mark_active("Strobe")
        dash.mark_completed("Strobe")
        rendered = dash._render()
        output = StringIO()
        console = Console(file=output, color_system=None)
        console.print(rendered)
        assert "Strobe" in output.getvalue()
