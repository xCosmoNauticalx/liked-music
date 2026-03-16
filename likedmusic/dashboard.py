"""Rich Live download dashboard for real-time progress display."""

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

console = Console()


class DownloadDashboard:
    """Tracks download progress and renders a Rich Live display.

    Usage:
        with DownloadDashboard(total=10) as dash:
            dash.mark_active("Artist - Song")
            ...
            dash.mark_completed("Artist - Song")
    """

    def __init__(self, total: int):
        self.total = total
        self.active: list[str] = []
        self.completed: list[str] = []
        self.errors: list[tuple[str, str]] = []
        self._live: Live | None = None

    def __enter__(self):
        self._live = Live(self._render(), console=console, refresh_per_second=4)
        self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.update(self._render())
            self._live.__exit__(*args)

    def mark_active(self, label: str) -> None:
        self.active.append(label)
        self._refresh()

    def mark_completed(self, label: str) -> None:
        if label in self.active:
            self.active.remove(label)
        self.completed.append(label)
        self._refresh()

    def mark_error(self, label: str, error: str) -> None:
        if label in self.active:
            self.active.remove(label)
        self.errors.append((label, error))
        self._refresh()

    def _refresh(self) -> None:
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Group:
        parts: list[Text] = []

        done = len(self.completed) + len(self.errors)
        parts.append(Text(f"Progress: {done}/{self.total}", style="bold"))
        parts.append(Text(""))

        for label in self.active:
            parts.append(Text(f"  \u25cf Downloading: {label}", style="green"))

        if self.active and self.errors:
            parts.append(Text(""))

        for label, err in self.errors:
            parts.append(Text(f"  \u2718 {label} \u2014 {err}", style="red"))

        if (self.active or self.errors) and self.completed:
            parts.append(Text(""))

        for label in self.completed:
            parts.append(Text(f"  \u2714 {label}", style="dim"))

        return Group(*parts)
