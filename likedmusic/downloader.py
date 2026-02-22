"""Download songs from YouTube Music via yt-dlp."""

import json
import time
import yt_dlp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from likedmusic.config import BROWSER_AUTH_PATH, DATA_DIR


def _write_cookie_file() -> Path | None:
    """Parse cookies from browser.json and write a Netscape-format cookie file.

    Returns the path to the cookie file, or None if browser.json is missing
    or contains no cookies.
    """
    try:
        headers = json.loads(BROWSER_AUTH_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    cookie_str = headers.get("cookie", "")
    if not cookie_str:
        return None

    cookie_path = DATA_DIR / "cookies.txt"
    lines = ["# Netscape HTTP Cookie File"]
    for pair in cookie_str.split("; "):
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        lines.append(f".youtube.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}")

    cookie_path.write_text("\n".join(lines) + "\n")
    return cookie_path


def download_song(video_id: str, output_dir: Path, max_retries: int = 3, cookiefile: Path | None = None) -> Path:
    """Download a single song from YouTube Music as an M4A audio file.

    This function downloads the best available audio from YouTube Music for the given
    video ID and converts it to M4A format using FFmpeg. If the file already exists,
    the download is skipped. The function implements exponential backoff retry logic
    to handle transient failures.

    Args:
        video_id: The YouTube Music video identifier for the song to download.
        output_dir: The directory path where the downloaded M4A file will be saved.
        max_retries: The maximum number of download attempts before raising an error.
                    Defaults to 3. Uses exponential backoff (1s, 2s, 4s) between retries.

    Returns:
        Path: The file system path to the downloaded M4A file.

    Raises:
        RuntimeError: If the download fails after all retry attempts have been exhausted.
                     The error message includes the video ID, number of attempts, and
                     the last encountered error.
    """
    output_path = output_dir / f"{video_id}.m4a"
    if output_path.exists():
        return output_path

    url = f"https://music.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(output_dir / f"{video_id}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    if cookiefile:
        opts["cookiefile"] = str(cookiefile)

    last_error = None
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return output_path
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)

    raise RuntimeError(
        f"Failed to download {video_id} after {max_retries} attempts: {last_error}"
    )


def download_songs(
    songs: list[dict],
    output_dir: Path,
    max_workers: int = 4,
) -> dict[str, Path]:
    """Download multiple songs using a thread pool.

    Returns {video_id: file_path} for successful downloads.
    Failed downloads are logged but don't halt the batch.
    """
    cookiefile = _write_cookie_file()
    results = {}
    failed = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for song in songs:
            video_id = song["videoId"]
            future = executor.submit(download_song, video_id, output_dir, cookiefile=cookiefile)
            futures[future] = song

        for future in as_completed(futures):
            song = futures[future]
            video_id = song["videoId"]
            title = song.get("title", video_id)
            try:
                path = future.result()
                results[video_id] = path
                print(f"  Downloaded: {title}")
            except Exception as e:
                failed.append((title, str(e)))
                print(f"  FAILED: {title} — {e}")

    if failed:
        print(f"\n{len(failed)} download(s) failed:")
        for title, error in failed:
            print(f"  - {title}: {error}")

    return results
