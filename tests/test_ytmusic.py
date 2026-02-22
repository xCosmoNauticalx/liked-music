"""Tests for ytmusic browser-auth setup logic.

_try_auto_setup() does a runtime `import rookiepy` so tests control rookiepy by
patching sys.modules before each call. _save_browser_json() is pure and tested
independently via a tmp_path fixture.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _save_browser_json
# ---------------------------------------------------------------------------


def test_save_browser_json_writes_required_headers(tmp_path):
    """Cookie dict is serialised into the header structure ytmusicapi expects."""
    from likedmusic import ytmusic

    cookie_dict = {"SAPISID": "abc123", "SID": "sid_val"}
    browser_path = tmp_path / "browser.json"

    with patch("likedmusic.ytmusic.BROWSER_AUTH_PATH", browser_path):
        ytmusic._save_browser_json(cookie_dict)

    saved = json.loads(browser_path.read_text())

    assert "SAPISID=abc123" in saved["cookie"]
    assert "SID=sid_val" in saved["cookie"]
    assert saved["x-origin"] == "https://music.youtube.com"
    assert saved["x-goog-authuser"] == "0"
    assert "user-agent" in saved


def test_save_browser_json_cookie_string_format(tmp_path):
    """Cookies are joined with '; ' separators."""
    from likedmusic import ytmusic

    cookie_dict = {"A": "1", "B": "2", "C": "3"}
    browser_path = tmp_path / "browser.json"

    with patch("likedmusic.ytmusic.BROWSER_AUTH_PATH", browser_path):
        ytmusic._save_browser_json(cookie_dict)

    saved = json.loads(browser_path.read_text())
    parts = set(saved["cookie"].split("; "))
    assert parts == {"A=1", "B=2", "C=3"}


# ---------------------------------------------------------------------------
# _try_auto_setup — rookiepy not available
# ---------------------------------------------------------------------------


def test_try_auto_setup_returns_false_when_rookiepy_missing(tmp_path):
    """Returns False without error when rookiepy is not installed."""
    from likedmusic.ytmusic import _try_auto_setup

    with patch.dict(sys.modules, {"rookiepy": None}):
        result = _try_auto_setup()

    assert result is False


# ---------------------------------------------------------------------------
# _try_auto_setup — rookiepy available
# ---------------------------------------------------------------------------


def _make_mock_rookiepy(cookies_by_browser: dict) -> MagicMock:
    """Return a rookiepy mock whose browser callables yield the given cookies.

    cookies_by_browser maps browser-name → list-of-cookie-dicts.
    Browsers absent from the dict raise RuntimeError when called.
    """
    mock_rp = MagicMock()

    def make_fn(cookies):
        """Return a callable that returns cookies regardless of domain arg."""
        def fn(domains=None):
            return cookies
        return fn

    for name, cookies in cookies_by_browser.items():
        setattr(mock_rp, name, make_fn(cookies))

    # vars(rookiepy) is used to enumerate browsers; set __dict__ accordingly.
    mock_rp.__dict__.update({
        name: getattr(mock_rp, name) for name in cookies_by_browser
    })

    return mock_rp


def test_try_auto_setup_returns_true_and_writes_file(tmp_path):
    """Writes browser.json and returns True when a browser has SAPISID."""
    from likedmusic.ytmusic import _try_auto_setup

    cookies = [{"name": "SAPISID", "value": "s3cr3t"}, {"name": "SID", "value": "sid"}]
    mock_rp = _make_mock_rookiepy({"chrome": cookies})
    browser_path = tmp_path / "browser.json"

    with (
        patch.dict(sys.modules, {"rookiepy": mock_rp}),
        patch("likedmusic.ytmusic.BROWSER_AUTH_PATH", browser_path),
    ):
        result = _try_auto_setup()

    assert result is True
    assert browser_path.exists()
    saved = json.loads(browser_path.read_text())
    assert "SAPISID=s3cr3t" in saved["cookie"]


def test_try_auto_setup_returns_false_when_no_browser_has_sapisid(tmp_path):
    """Returns False when every browser's cookie jar lacks SAPISID."""
    from likedmusic.ytmusic import _try_auto_setup

    # One browser present but missing SAPISID.
    cookies = [{"name": "SID", "value": "only_sid"}]
    mock_rp = _make_mock_rookiepy({"chrome": cookies})
    browser_path = tmp_path / "browser.json"

    with (
        patch.dict(sys.modules, {"rookiepy": mock_rp}),
        patch("likedmusic.ytmusic.BROWSER_AUTH_PATH", browser_path),
    ):
        result = _try_auto_setup()

    assert result is False
    assert not browser_path.exists()


def test_try_auto_setup_skips_failing_browsers_and_uses_next(tmp_path):
    """A browser that raises does not prevent subsequent browsers from being tried."""
    from likedmusic.ytmusic import _try_auto_setup

    def failing_chrome(domains=None):
        raise RuntimeError("keychain locked")

    good_cookies = [{"name": "SAPISID", "value": "found"}]

    def working_firefox(domains=None):
        return good_cookies

    mock_rp = MagicMock()
    mock_rp.__dict__.update({"chrome": failing_chrome, "firefox": working_firefox})
    browser_path = tmp_path / "browser.json"

    with (
        patch.dict(sys.modules, {"rookiepy": mock_rp}),
        patch("likedmusic.ytmusic.BROWSER_AUTH_PATH", browser_path),
    ):
        result = _try_auto_setup()

    assert result is True
    saved = json.loads(browser_path.read_text())
    assert "SAPISID=found" in saved["cookie"]


def test_try_auto_setup_no_browser_functions_returns_false(tmp_path):
    """Returns False when rookiepy exports no callable browser functions."""
    from likedmusic.ytmusic import _try_auto_setup

    # An effectively empty rookiepy (no callable exports).
    mock_rp = MagicMock()
    mock_rp.__dict__.clear()
    browser_path = tmp_path / "browser.json"

    with (
        patch.dict(sys.modules, {"rookiepy": mock_rp}),
        patch("likedmusic.ytmusic.BROWSER_AUTH_PATH", browser_path),
    ):
        result = _try_auto_setup()

    assert result is False


# ---------------------------------------------------------------------------
# resolve_playlist_id
# ---------------------------------------------------------------------------


def test_resolve_playlist_id_found():
    from likedmusic.ytmusic import resolve_playlist_id

    mock_ytm = MagicMock()
    mock_ytm.get_library_playlists.return_value = [
        {"title": "Chill Vibes", "playlistId": "PL_chill"},
        {"title": "EDM Bangers", "playlistId": "PL_edm"},
    ]

    with patch("likedmusic.ytmusic._get_ytm_client", return_value=mock_ytm):
        result = resolve_playlist_id("EDM Bangers")

    assert result == "PL_edm"


def test_resolve_playlist_id_not_found():
    from likedmusic.ytmusic import resolve_playlist_id

    mock_ytm = MagicMock()
    mock_ytm.get_library_playlists.return_value = [
        {"title": "Chill Vibes", "playlistId": "PL_chill"},
    ]

    with patch("likedmusic.ytmusic._get_ytm_client", return_value=mock_ytm):
        with pytest.raises(ValueError, match="not found"):
            resolve_playlist_id("Nonexistent")


def test_fetch_playlist_songs():
    from likedmusic.ytmusic import fetch_playlist_songs

    mock_ytm = MagicMock()
    mock_ytm.get_playlist.return_value = {
        "tracks": [{"videoId": "abc", "title": "Song"}],
    }

    with patch("likedmusic.ytmusic._get_ytm_client", return_value=mock_ytm):
        tracks = fetch_playlist_songs("PL_test")

    assert len(tracks) == 1
    assert tracks[0]["videoId"] == "abc"
    mock_ytm.get_playlist.assert_called_once_with("PL_test", limit=5000)
