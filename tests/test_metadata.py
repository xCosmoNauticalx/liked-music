"""Tests for likedmusic.metadata — parse_title_artist and get_best_thumbnail_url."""

from likedmusic.metadata import get_best_thumbnail_url, parse_title_artist


class TestParseTitleArtist:
    def test_dash_split_no_artists(self):
        title, artist = parse_title_artist("Daft Punk - Get Lucky", None)
        assert title == "Get Lucky"
        assert artist == "Daft Punk"

    def test_dash_split_empty_artists(self):
        title, artist = parse_title_artist("Daft Punk - Get Lucky", [])
        assert title == "Get Lucky"
        assert artist == "Daft Punk"

    def test_dash_split_matching_artist_prefix(self):
        title, artist = parse_title_artist(
            "Daft Punk - Get Lucky",
            [{"name": "Daft Punk"}],
        )
        assert title == "Get Lucky"
        assert artist == "Daft Punk"

    def test_dash_split_non_matching_prefix(self):
        title, artist = parse_title_artist(
            "Daft Punk - Get Lucky",
            [{"name": "Someone Else"}],
        )
        assert title == "Daft Punk - Get Lucky"
        assert artist == "Someone Else"

    def test_no_dash(self):
        title, artist = parse_title_artist(
            "Get Lucky",
            [{"name": "Daft Punk"}],
        )
        assert title == "Get Lucky"
        assert artist == "Daft Punk"

    def test_no_dash_no_artists(self):
        title, artist = parse_title_artist("Get Lucky", None)
        assert title == "Get Lucky"
        assert artist == ""

    def test_multiple_artists(self):
        title, artist = parse_title_artist(
            "Get Lucky",
            [{"name": "Daft Punk"}, {"name": "Pharrell Williams"}],
        )
        assert title == "Get Lucky"
        assert artist == "Daft Punk, Pharrell Williams"

    def test_empty_artists_list(self):
        title, artist = parse_title_artist("Song", [])
        assert title == "Song"
        assert artist == ""


class TestGetBestThumbnailUrl:
    def test_none_input(self):
        assert get_best_thumbnail_url(None) is None

    def test_empty_list(self):
        assert get_best_thumbnail_url([]) is None

    def test_single_thumbnail(self):
        thumbs = [{"url": "http://img.com/1.jpg", "width": 120}]
        assert get_best_thumbnail_url(thumbs) == "http://img.com/1.jpg"

    def test_multiple_resolutions(self):
        thumbs = [
            {"url": "http://img.com/small.jpg", "width": 120},
            {"url": "http://img.com/large.jpg", "width": 1280},
            {"url": "http://img.com/medium.jpg", "width": 480},
        ]
        assert get_best_thumbnail_url(thumbs) == "http://img.com/large.jpg"

    def test_missing_width_key(self):
        thumbs = [
            {"url": "http://img.com/nowidth.jpg"},
            {"url": "http://img.com/haswidth.jpg", "width": 100},
        ]
        assert get_best_thumbnail_url(thumbs) == "http://img.com/haswidth.jpg"
