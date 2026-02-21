"""YouTube Music API wrapper for fetching liked songs."""

from ytmusicapi import YTMusic, setup_oauth

from likedmusic.config import OAUTH_PATH


def setup_ytmusic_oauth(client_id: str, client_secret: str) -> None:
    """Run interactive OAuth flow and save credentials."""
    setup_oauth(
        client_id=client_id,
        client_secret=client_secret,
        filepath=str(OAUTH_PATH),
    )
    print(f"OAuth credentials saved to {OAUTH_PATH}")


def fetch_liked_songs(client_id: str, client_secret: str) -> list[dict]:
    """Fetch liked songs from YouTube Music.

    Returns list of track dicts with videoId, title, artists, album, thumbnails.
    """
    if not OAUTH_PATH.exists():
        raise FileNotFoundError(
            f"OAuth credentials not found at {OAUTH_PATH}. "
            "Run 'likedmusic setup' first."
        )

    ytm = YTMusic(str(OAUTH_PATH), oauth_credentials={
        "client_id": client_id,
        "client_secret": client_secret,
    })
    response = ytm.get_liked_songs(limit=5000)
    tracks = response.get("tracks", [])
    print(f"Fetched {len(tracks)} liked songs from YouTube Music")
    return tracks
