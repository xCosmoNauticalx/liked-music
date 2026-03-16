"""YouTube Music API wrapper for fetching liked songs.

Authentication uses ytmusicapi's browser-auth mode. The browser.json file holds
HTTP request headers (including a Cookie string) extracted from a live browser
session logged into music.youtube.com. ytmusicapi reads those headers and
computes a per-request SAPISIDHASH Authorization header from the SAPISID cookie.

Setup can be automated via rookiepy, which reads the browser's on-disk cookie
store without any user interaction. On macOS, Chrome cookies are encrypted with
the login keychain — the OS will prompt for the user's password on the first
extraction. Firefox and Safari cookies are accessible without a password prompt.
"""

import json
import logging
import time
import hashlib
from ytmusicapi import YTMusic, setup

from likedmusic import const
from likedmusic.config import BROWSER_AUTH_PATH

logger = logging.getLogger(__name__)


# ytmusicapi 1.11+ reads __Secure-3PAPISID to compute SAPISIDHASH on each request.
# SAPISID is the older equivalent accepted as a fallback.
_REQUIRED_COOKIES = {"__Secure-3PAPISID", "SAPISID"}  # at least one must be present
_YTM_ORIGIN = "https://music.youtube.com"


def _has_required_cookies(cookie_dict: dict) -> bool:
    """Check if the cookie dictionary contains at least one required cookie.

    ytmusicapi requires either __Secure-3PAPISID (preferred in 1.11+) or
    SAPISID (legacy fallback) to compute the SAPISIDHASH authorization header.
    This function verifies that at least one of these cookies is present.

    Args:
        cookie_dict: Dictionary mapping cookie names to their values, typically
                     extracted from a browser's cookie store for youtube.com.

    Returns:
        True if at least one required cookie (__Secure-3PAPISID or SAPISID)
        is present in the dictionary, False otherwise.
    """
    return bool(_REQUIRED_COOKIES & cookie_dict.keys())


def _compute_sapisidhash(sapisid: str) -> str:
    """Compute SAPISIDHASH value from SAPISID cookie (time-based SHA1).

    ytmusicapi recomputes this on every request using the live cookie value.
    The stored value in browser.json is only used to identify the file as
    browser-auth (not OAuth) during YTMusic initialisation.

    The SAPISIDHASH is computed by concatenating the current Unix timestamp,
    the SAPISID cookie value, and the YouTube Music origin URL, then hashing
    the result with SHA1. The final format is "SAPISIDHASH {timestamp}_{hash}".

    Args:
        sapisid: The SAPISID or __Secure-3PAPISID cookie value extracted from
                 the browser's cookie store for youtube.com. This cookie is
                 used by Google services for authentication.

    Returns:
        A string in the format "SAPISIDHASH {timestamp}_{hash}" where timestamp
        is the current Unix time in seconds and hash is the SHA1 hexdigest of
        the concatenated timestamp, SAPISID value, and origin URL.
    """
    timestamp = str(int(time.time()))
    sha1 = hashlib.sha1()
    sha1.update(f"{timestamp} {sapisid} {_YTM_ORIGIN}".encode("utf-8"))
    return f"SAPISIDHASH {timestamp}_{sha1.hexdigest()}"


def _save_browser_json(cookie_dict: dict, browser_name: str | None = None) -> None:
    """Write browser.json in the format ytmusicapi 1.11+ expects.

    ytmusicapi detects browser-auth by checking that the ``authorization``
    header contains ``"SAPISIDHASH"``; if that header is absent the library
    falls back to treating the file as OAuth credentials and raises an error.
    All header keys must be lowercase to match ytmusicapi's CaseInsensitiveDict
    normalisation and ``is_browser()`` check.

    Args:
        cookie_dict: Mapping of cookie name → value, already filtered to the
                     youtube.com domain.
        browser_name: Name of the browser cookies were extracted from (e.g.
                      "chrome", "firefox"). Stored in browser.json so the
                      downloader can use yt-dlp's cookiesfrombrowser option.
    """
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookie_dict.items())
    # Prefer __Secure-3PAPISID (required by ytmusicapi 1.11+); fall back to SAPISID.
    sapisid = cookie_dict.get("__Secure-3PAPISID") or cookie_dict.get("SAPISID", "")
    headers = {
        # A real Chrome UA is required; YouTube Music returns errors for
        # unrecognised or bot-like user agents.
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.5",
        "content-type": "application/json",
        # Required by ytmusicapi 1.11+ to identify this as browser-auth.
        # ytmusicapi recomputes the hash on each API request from the cookie.
        "authorization": _compute_sapisidhash(sapisid),
        # Selects the first signed-in Google account (0-indexed).
        "x-goog-authuser": "0",
        "x-origin": _YTM_ORIGIN,
        "cookie": cookie_str,
    }
    if browser_name:
        headers["_browser"] = browser_name
    BROWSER_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    BROWSER_AUTH_PATH.write_text(json.dumps(headers, indent=4))


def _try_auto_setup() -> bool:
    """Try to extract YouTube Music cookies from installed browsers.

    Uses rookiepy to read each browser's on-disk cookie store. Browsers are
    discovered dynamically from rookiepy's public API — no static list is
    maintained here. The first browser that yields a cookie jar containing
    at least one required cookie (__Secure-3PAPISID or SAPISID) wins; its
    cookies are written to browser.json.

    On macOS, Chrome encrypts cookies with the login keychain. The OS will
    show a single password-prompt dialog on the first extraction. Firefox and
    Safari do not require this prompt.

    The function iterates through all available browser extractor functions
    provided by rookiepy, attempting to extract youtube.com cookies from each.
    If a browser is not installed, locked, or cookie decryption fails, the
    function silently continues to the next browser. The first successful
    extraction that contains the required authentication cookies is saved.

    Returns:
        bool: True if browser.json was written successfully with valid YouTube
              Music authentication cookies, False if rookiepy is not installed
              or no browser yielded the required cookies.
    """

    try:
        import rookiepy
    except ImportError:
        return False

    # Enumerate every public callable that rookiepy exports. Each one is a
    # browser extractor function that accepts a list of domain filters.
    browser_fns = {
        name: fn
        for name, fn in vars(rookiepy).items()
        if not name.startswith("_") and callable(fn)
    }

    for name, fn in browser_fns.items():
        try:
            # Restrict to youtube.com cookies so we don't handle a huge jar.
            cookies = fn(["youtube.com"])
        except Exception as e:
            # Browser not installed, locked, or decryption failed — try next.
            logger.debug("Browser %s unavailable: %s", name, e)
            cookies = []

        cookie_dict = {c[const.NAME_KEY]: c[const.VALUE_KEY] for c in cookies}

        if _has_required_cookies(cookie_dict):
            _save_browser_json(cookie_dict, browser_name=name)
            print(f"Auto-extracted YouTube Music cookies from {name}.")
            print(f"Saved to {BROWSER_AUTH_PATH}")
            return True

    return False


def setup_ytmusic_browser() -> None:
    """Set up YouTube Music browser authentication by extracting or prompting for credentials.

    This function establishes the authentication configuration required for YouTube Music API
    access. It first attempts automatic cookie extraction from installed browsers using rookiepy,
    which reads browser cookie stores to obtain the necessary authentication tokens
    (__Secure-3PAPISID or SAPISID). If automatic extraction fails—due to rookiepy not being
    installed, no browser being logged into YouTube Music, or cookie decryption being
    unavailable—the function falls back to ytmusicapi's interactive setup flow, which prompts
    the user to manually paste HTTP request headers from their browser's DevTools.

    The extracted or manually provided credentials are saved to a browser.json file at the
    location specified by BROWSER_AUTH_PATH. This file contains HTTP headers (including cookies)
    that ytmusicapi uses to authenticate subsequent API requests.

    On macOS, automatic extraction from Chrome may trigger a system keychain password prompt
    on first use, as Chrome encrypts cookies with the login keychain. Firefox and Safari do
    not require this prompt.

    Returns:
        None: This function performs side effects (writes browser.json and prints status
              messages) but does not return a value.

    Raises:
        This function does not explicitly raise exceptions, but the underlying ytmusicapi
        setup() call may raise exceptions if the user provides invalid headers during
        manual setup.
    """
    if _try_auto_setup():
        return

    print("Could not auto-extract cookies from any browser.")
    print("Falling back to manual setup — paste request headers from browser DevTools.")
    setup(filepath=str(BROWSER_AUTH_PATH))
    print(f"Browser auth headers saved to {BROWSER_AUTH_PATH}")


def _get_ytm_client() -> YTMusic:
    """Create an authenticated YTMusic client using browser authentication headers.

    This function initializes a YTMusic API client by loading the browser authentication
    headers from the browser.json file. The headers file must have been previously created
    by running the setup process (either automatic via rookiepy or manual via ytmusicapi's
    interactive setup). The file contains HTTP request headers including cookies
    (__Secure-3PAPISID or SAPISID) that ytmusicapi uses to authenticate API requests to
    YouTube Music.

    Returns:
        YTMusic: An authenticated YTMusic client instance ready to make API calls to
                 YouTube Music services. The client uses the browser authentication
                 headers stored in browser.json to authorize requests.

    Raises:
        FileNotFoundError: If the browser.json authentication file does not exist at
                          BROWSER_AUTH_PATH. This indicates that the setup process
                          has not been completed. Users should run 'likedmusic setup'
                          to create the required authentication file.
    """
    if not BROWSER_AUTH_PATH.is_file():
        raise FileNotFoundError(
            f"Browser auth headers not found at {BROWSER_AUTH_PATH}. "
            "Run 'likedmusic setup' first."
        )
    return YTMusic(str(BROWSER_AUTH_PATH))


def fetch_liked_songs() -> list[dict]:
    """Fetch all liked songs from the authenticated YouTube Music account.

    This function retrieves up to 5000 liked songs from YouTube Music using the
    authenticated YTMusic client. Each track in the returned list contains metadata
    including the video ID, title, artist information, album details, and thumbnail
    URLs. The function prints the total number of fetched tracks to stdout.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a liked
                    song with the following keys:
                    - videoId (str): The unique YouTube video identifier for the track
                    - title (str): The song title
                    - artists (list): List of artist information dictionaries
                    - album (dict): Album information including name and ID
                    - thumbnails (list): List of thumbnail image URLs in various sizes
                    Returns an empty list if no liked songs are found or if the API
                    request fails to return tracks.

    Raises:
        FileNotFoundError: If the browser authentication file does not exist at
                          BROWSER_AUTH_PATH, raised by _get_ytm_client().
    """
    ytm = _get_ytm_client()
    response = ytm.get_liked_songs(limit=5000)
    tracks = response.get(const.TRACKS_KEY, [])
    print(f"Fetched {len(tracks)} liked songs from YouTube Music")
    return tracks


def fetch_playlist_songs(playlist_id: str) -> list[dict]:
    """Fetch all tracks from a specified YouTube Music playlist.

    This function retrieves up to 5000 tracks from a YouTube Music playlist using the
    authenticated YTMusic client. Each track in the returned list contains metadata
    including the video ID, title, artist information, album details, and thumbnail
    URLs. The function prints the total number of fetched tracks to stdout.

    Args:
        playlist_id: The unique identifier for the YouTube Music playlist. This ID
                     can be obtained from the playlist URL or by using the
                     resolve_playlist_id() function to convert a playlist name to
                     its corresponding ID.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a track
                    from the playlist with the following keys:
                    - videoId (str): The unique YouTube video identifier for the track
                    - title (str): The song title
                    - artists (list): List of artist information dictionaries
                    - album (dict): Album information including name and ID
                    - thumbnails (list): List of thumbnail image URLs in various sizes
                    Returns an empty list if the playlist is empty or if the API
                    request fails to return tracks.

    Raises:
        FileNotFoundError: If the browser authentication file does not exist at
                          BROWSER_AUTH_PATH, raised by _get_ytm_client().
    """
    ytm = _get_ytm_client()
    response = ytm.get_playlist(playlist_id, limit=5000)
    tracks = response.get(const.TRACKS_KEY, [])
    print(f"Fetched {len(tracks)} tracks from playlist")
    return tracks


def resolve_playlist_id(playlist_name: str) -> str:
    """Resolve a YouTube Music playlist name to its unique playlist identifier.

    This function searches through all playlists in the authenticated user's YouTube Music
    library to find a playlist matching the provided name. The search is case-sensitive and
    requires an exact match. If the playlist is found, its unique identifier is returned,
    which can be used with other YouTube Music API functions such as fetch_playlist_songs().

    Args:
        playlist_name: The exact name of the YouTube Music playlist to search for. The name
                       must match a playlist in the user's library exactly (case-sensitive).

    Returns:
        str: The unique playlist identifier (playlistId) for the matching playlist. This ID
             can be used to fetch tracks or perform other operations on the playlist.

    Raises:
        ValueError: If no playlist with the specified name is found in the user's library.
                   The error message includes a comma-separated list of all available
                   playlist names to help the user identify the correct playlist name.
        FileNotFoundError: If the browser authentication file does not exist at
                          BROWSER_AUTH_PATH, raised by _get_ytm_client().
    """
    ytm = _get_ytm_client()
    library = ytm.get_library_playlists(limit=None)
    for entry in library:
        if entry.get(const.TITLE_KEY) == playlist_name:
            return entry["playlistId"]
    available = [p.get(const.TITLE_KEY, "?") for p in library]
    raise ValueError(
        f"Playlist '{playlist_name}' not found. "
        f"Available playlists: {', '.join(available)}"
    )
