"""Embed metadata and album art into M4A files."""

from pathlib import Path

import requests
from mutagen.mp4 import MP4, MP4Cover


def parse_title_artist(title: str, artists: list[dict] | None) -> tuple[str, str]:
    """Clean up title and artist fields.

    If title contains "Artist - Song Title" and artists list is empty or matches,
    split accordingly. Otherwise use structured fields as-is.
    """
    artist_names = []
    if artists:
        artist_names = [a["name"] for a in artists if a.get("name")]

    artist_str = ", ".join(artist_names) if artist_names else ""

    if " - " in title:
        parts = title.split(" - ", 1)
        prefix = parts[0].strip()
        suffix = parts[1].strip()

        # Use split if artists is empty or the prefix matches an artist
        if not artist_names or prefix == artist_names[0]:
            return suffix, prefix

    return title, artist_str


def get_best_thumbnail_url(thumbnails: list[dict] | None) -> str | None:
    """Pick the highest-resolution thumbnail URL."""
    if not thumbnails:
        return None
    sorted_thumbs = sorted(thumbnails, key=lambda t: t.get("width", 0), reverse=True)
    return sorted_thumbs[0].get("url")


def embed_metadata(
    file_path: Path,
    title: str,
    artist: str,
    album: str | None = None,
    thumbnail_url: str | None = None,
) -> None:
    """Embed title, artist, album, and cover art into an M4A file."""
    audio = MP4(str(file_path))

    audio["\xa9nam"] = [title]
    audio["\xa9ART"] = [artist]
    if album:
        audio["\xa9alb"] = [album]

    if thumbnail_url:
        try:
            resp = requests.get(thumbnail_url, timeout=10)
            resp.raise_for_status()
            image_data = resp.content

            # Detect format from content type
            content_type = resp.headers.get("content-type", "")
            if "png" in content_type:
                fmt = MP4Cover.FORMAT_PNG
            else:
                fmt = MP4Cover.FORMAT_JPEG

            audio["covr"] = [MP4Cover(image_data, imageformat=fmt)]
        except Exception as e:
            print(f"  Warning: Could not download album art for {title}: {e}")

    audio.save()
