"""AppleScript wrapper for Apple Music (Music.app) playlist management."""

import subprocess
from pathlib import Path


def _escape_applescript_string(s: str) -> str:
    """Escape a string for use inside AppleScript double quotes."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def run_applescript(script: str) -> str:
    """Run an AppleScript and return stdout. Raises on failure."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"AppleScript failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def ensure_playlist(name: str) -> None:
    """Create the playlist if it doesn't already exist."""
    escaped = _escape_applescript_string(name)
    script = f'''
tell application "Music"
    if not (exists playlist "{escaped}") then
        make new playlist with properties {{name:"{escaped}"}}
    end if
end tell
'''
    run_applescript(script)


def clear_playlist(name: str) -> None:
    """Remove all tracks from a playlist (fallback only)."""
    escaped = _escape_applescript_string(name)
    script = f'''
tell application "Music"
    if exists playlist "{escaped}" then
        delete every track of playlist "{escaped}"
    end if
end tell
'''
    run_applescript(script)


def add_track_to_playlist(file_path: Path, playlist_name: str) -> None:
    """Add a single M4A file to the playlist."""
    escaped_playlist = _escape_applescript_string(playlist_name)
    posix_path = str(file_path.resolve())
    escaped_path = _escape_applescript_string(posix_path)
    script = f'''
tell application "Music"
    add POSIX file "{escaped_path}" to playlist "{escaped_playlist}"
end tell
'''
    run_applescript(script)


def add_tracks_to_playlist(file_paths: list[Path], playlist_name: str) -> None:
    """Add multiple tracks to playlist sequentially to preserve order."""
    for path in file_paths:
        add_track_to_playlist(path, playlist_name)


def get_playlist_track_names(playlist_name: str) -> list[str]:
    """Return current track names in playlist order."""
    escaped = _escape_applescript_string(playlist_name)
    script = f'''
tell application "Music"
    if exists playlist "{escaped}" then
        get name of every track of playlist "{escaped}"
    else
        return ""
    end if
end tell
'''
    result = run_applescript(script)
    if not result:
        return []
    return [name.strip() for name in result.split(", ")]


def reorder_playlist(playlist_name: str, ordered_track_names: list[str]) -> None:
    """Reorder tracks in-place by moving each to the end in desired order.

    For each track name in the desired order, find it in the playlist and move
    it to the end. After processing all tracks, the playlist matches the desired order.
    """
    escaped_playlist = _escape_applescript_string(playlist_name)

    for track_name in ordered_track_names:
        escaped_name = _escape_applescript_string(track_name)
        script = f'''
tell application "Music"
    set targetPlaylist to playlist "{escaped_playlist}"
    set trackList to (every track of targetPlaylist whose name is "{escaped_name}")
    if (count of trackList) > 0 then
        set targetTrack to item 1 of trackList
        move targetTrack to end of targetPlaylist
    end if
end tell
'''
        try:
            run_applescript(script)
        except RuntimeError as e:
            print(f"  Warning: Could not move track '{track_name}': {e}")
