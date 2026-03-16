"""Download songs from YouTube Music via yt-dlp."""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
import yt_dlp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from likedmusic.config import BROWSER_AUTH_PATH, DATA_DIR

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from likedmusic.dashboard import DownloadDashboard

_LOG_FILE = DATA_DIR / "downloader.log"
_REPO_LOG_FILE = Path(__file__).resolve().parent.parent / "downloader.log"
_COOKIE_FILE = DATA_DIR / "cookies.txt"


def _find_js_runtime() -> dict:
    """Detect an installed JS runtime for yt-dlp's EJS challenge solver."""
    for runtime in ("deno", "node", "bun"):
        if shutil.which(runtime):
            return {runtime: {}}
    return {}


def _check_ffmpeg() -> str | None:
    """Locate ffmpeg + ffprobe for yt-dlp post-processing."""
    # Tier 1: both on system PATH (e.g. brew install ffmpeg)
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return None

    # Tier 2: static-ffmpeg pip package (bundles both binaries)
    try:
        from static_ffmpeg import run
        ffmpeg_path, ffprobe_path = run.get_or_fetch_platform_executables_else_raise()
        return str(Path(ffmpeg_path).parent)
    except (ImportError, Exception):
        pass

    # Tier 3: only ffmpeg on PATH (no ffprobe) — yt-dlp may still work
    if shutil.which("ffmpeg"):
        logger.warning(
            "ffprobe not found — post-processing may fail. "
            "Install ffmpeg fully: brew install ffmpeg"
        )
        return None

    raise RuntimeError(
        "ffmpeg is required but not found. "
        "Install it with: brew install ffmpeg  OR  pip install static-ffmpeg"
    )


def _extract_cookies() -> Path | None:
    """Extract browser cookies to a shared file (one Keychain prompt)."""
    try:
        headers = json.loads(BROWSER_AUTH_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    browser_name = headers.get("_browser")
    if not browser_name:
        return None

    try:
        opts: dict = {
            "cookiesfrombrowser": (browser_name,),
            "cookiefile": str(_COOKIE_FILE),
            "remote_components": ["ejs:github"],
            "logger": logger,
        }
        js_rt = _find_js_runtime()
        if js_rt:
            opts["js_runtimes"] = js_rt
        with yt_dlp.YoutubeDL(opts) as ydl:
            _ = ydl.cookiejar  # triggers lazy cookie loading; __exit__ saves to file
    except Exception:
        logger.warning("Failed to extract cookies from %s", browser_name)
        return None

    if not _COOKIE_FILE.exists():
        logger.warning("Cookie file was not created after extraction")
        return None

    try:
        os.chmod(_COOKIE_FILE, 0o600)
    except OSError:
        pass

    return _COOKIE_FILE


def _setup_logging() -> None:
    """Add file handlers to the downloader logger if not already configured."""
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    # Primary log in ~/.likedmusic/
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    h1 = logging.FileHandler(_LOG_FILE)
    h1.setFormatter(fmt)
    logger.addHandler(h1)
    # Copy in the repo folder for easy access
    h2 = logging.FileHandler(_REPO_LOG_FILE)
    h2.setFormatter(fmt)
    logger.addHandler(h2)
    logger.setLevel(logging.DEBUG)


def download_song(
    video_id: str,
    output_dir: Path,
    max_retries: int = 3,
    cookiefile: Path | None = None,
    ffmpeg_location: str | None = None,
) -> Path:
    """Download a single song from YouTube Music as an M4A audio file.

    Args:
        video_id: The YouTube Music video identifier for the song to download.
        output_dir: The directory path where the downloaded M4A file will be saved.
        max_retries: The maximum number of download attempts before raising an error.
                    Defaults to 3. Uses exponential backoff (1s, 2s, 4s) between retries.
        cookiefile: Path to a Netscape cookie file for authentication.

    Returns:
        Path: The file system path to the downloaded M4A file.

    Raises:
        RuntimeError: If the download fails after all retry attempts have been exhausted.
    """
    output_path = output_dir / f"{video_id}.m4a"
    if output_path.exists():
        return output_path

    url = f"https://music.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "extractor_args": {"youtube": {"player_js_variant": ["main"]}},
        "remote_components": ["ejs:github"],
        "outtmpl": str(output_dir / f"{video_id}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }],
        "logger": logger,
    }
    js_rt = _find_js_runtime()
    if js_rt:
        opts["js_runtimes"] = js_rt
    if cookiefile:
        opts["cookiefile"] = str(cookiefile)
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location

    last_error = None
    for attempt in range(max_retries):
        logger.debug("Download attempt %d/%d for %s", attempt + 1, max_retries, video_id)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return output_path
        except Exception as e:
            last_error = e
            logger.warning("Download attempt %d failed for %s: %s", attempt + 1, video_id, e)
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
    dashboard: DownloadDashboard | None = None,
) -> dict[str, Path]:
    """Download multiple songs using a thread pool.

    Returns {video_id: file_path} for successful downloads.
    Failed downloads are logged but don't halt the batch.
    """
    ffmpeg_location = _check_ffmpeg()
    cookiefile = _extract_cookies()
    _setup_logging()
    results = {}
    failed = []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for song in songs:
                video_id = song["videoId"]
                title = song.get("title", video_id)
                if dashboard:
                    dashboard.mark_active(title)
                future = executor.submit(download_song, video_id, output_dir, cookiefile=cookiefile, ffmpeg_location=ffmpeg_location)
                futures[future] = song

            for future in as_completed(futures):
                song = futures[future]
                video_id = song["videoId"]
                title = song.get("title", video_id)
                try:
                    path = future.result()
                    results[video_id] = path
                    if dashboard:
                        dashboard.mark_completed(title)
                    else:
                        print(f"  Downloaded: {title}")
                except Exception as e:
                    failed.append((title, str(e)))
                    if dashboard:
                        dashboard.mark_error(title, str(e))
                    else:
                        print(f"  FAILED: {title} — {e}")

        if not dashboard and failed:
            print(f"\n{len(failed)} download(s) failed:")
            for title, error in failed:
                print(f"  - {title}: {error}")
    finally:
        if cookiefile and cookiefile.exists():
            try:
                cookiefile.unlink()
            except OSError:
                pass

    return results
