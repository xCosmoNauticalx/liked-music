"""YouTube Music API wrapper for fetching liked songs."""

from ytmusicapi import YTMusic, setup

from likedmusic.config import BROWSER_AUTH_PATH


def setup_ytmusic_browser() -> None:
    """Run interactive browser headers setup and save to disk."""
    setup(filepath=str(BROWSER_AUTH_PATH))
    print(f"Browser auth headers saved to {BROWSER_AUTH_PATH}")


def fetch_liked_songs() -> list[dict]:
    """Fetch liked songs from YouTube Music.

    Returns list of track dicts with videoId, title, artists, album, thumbnails.
    """
    try:
        ytm = YTMusic(str(BROWSER_AUTH_PATH))
    except Exception as e:
        raise FileNotFoundError(
            f"Browser auth headers not found at {BROWSER_AUTH_PATH}. "
            "Run 'likedmusic setup' first."
        ) from e
    response = ytm.get_liked_songs(limit=5000)
    tracks = response.get("tracks", [])
    print(f"Fetched {len(tracks)} liked songs from YouTube Music")
    return tracks
