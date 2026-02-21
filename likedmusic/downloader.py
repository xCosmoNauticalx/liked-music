"""Download songs from YouTube Music via yt-dlp."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yt_dlp


def download_song(video_id: str, output_dir: Path, max_retries: int = 3) -> Path:
    """Download a single song as M4A. Returns path to downloaded file.

    Retries up to max_retries times with exponential backoff.
    Skips download if file already exists.
    """
    output_path = output_dir / f"{video_id}.m4a"
    if output_path.exists():
        return output_path

    url = f"https://music.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }],
        "outtmpl": str(output_dir / f"{video_id}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

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
    results = {}
    failed = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for song in songs:
            video_id = song["videoId"]
            future = executor.submit(download_song, video_id, output_dir)
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
