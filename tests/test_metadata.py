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
        """Title split wins over channel name in artists list."""
        title, artist = parse_title_artist(
            "Daft Punk - Get Lucky",
            [{"name": "Someone Else"}],
        )
        assert title == "Get Lucky"
        assert artist == "Daft Punk"

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


class TestRemixParsing:
    def test_bare_remix_suffix(self):
        """Case A: suffix starts with bare remix pattern."""
        title, artist = parse_title_artist(
            "crystallized - Subtronics Remix (feat. Inez)",
            [{"name": "John Summit"}],
        )
        assert title == "crystallized (Subtronics Remix) (feat. Inez)"
        assert artist == "John Summit, Subtronics"

    def test_standard_split_with_remix_parens(self):
        """Case B: standard artist-title with remix in parens."""
        title, artist = parse_title_artist(
            "Labrinth - Mount Everest (YDG & Kade Findley Remix)",
            [{"name": "YDG"}],
        )
        assert title == "Mount Everest (YDG & Kade Findley Remix)"
        assert artist == "Labrinth, YDG, Kade Findley"

    def test_pipe_tags_and_x_collab(self):
        """Case C: pipe tags stripped, x-collaboration kept together."""
        title, artist = parse_title_artist(
            "HAVEN. - I Run (HerShe x Roto FLIP) | Dubstep | The Cue List",
            [{"name": "The Cue List"}],
        )
        assert title == "I Run (HerShe x Roto FLIP)"
        assert artist == "HAVEN., HerShe x Roto"

    def test_simple_remix_ignore_channel(self):
        """Case D: simple remix, structured artist (channel) ignored."""
        title, artist = parse_title_artist(
            "Artemas - I like the way you kiss me (YDG Remix)",
            [{"name": "Dubstep uNk"}],
        )
        assert title == "I like the way you kiss me (YDG Remix)"
        assert artist == "Artemas, YDG"


class TestRemixEdgeCases:
    def test_bare_flip_case_insensitive(self):
        title, artist = parse_title_artist(
            "song name - DJ Name FLIP",
            [{"name": "Channel"}],
        )
        assert title == "song name (DJ Name FLIP)"
        assert artist == "Channel, DJ Name"

    def test_bare_edit_suffix(self):
        title, artist = parse_title_artist(
            "original track - SomeProducer Edit",
            [{"name": "Original Artist"}],
        )
        assert title == "original track (SomeProducer Edit)"
        assert artist == "Original Artist, SomeProducer"

    def test_ampersand_splits_remixers_in_parens(self):
        title, artist = parse_title_artist(
            "Artist - Track (A & B & C Remix)",
            [{"name": "Channel"}],
        )
        assert title == "Track (A & B & C Remix)"
        assert artist == "Artist, A, B, C"

    def test_x_collab_not_split(self):
        title, artist = parse_title_artist(
            "Artist - Track (Foo x Bar Remix)",
            [{"name": "Channel"}],
        )
        assert title == "Track (Foo x Bar Remix)"
        assert artist == "Artist, Foo x Bar"

    def test_pipe_tags_no_remix(self):
        title, artist = parse_title_artist(
            "Artist - Song Title | Genre | Channel",
            [{"name": "Channel"}],
        )
        assert title == "Song Title"
        assert artist == "Artist"

    def test_feat_preserved_not_extracted(self):
        title, artist = parse_title_artist(
            "Artist - Song (feat. Singer)",
            [{"name": "Channel"}],
        )
        assert title == "Song (feat. Singer)"
        assert artist == "Artist"

    def test_dedup_remixer_already_in_structured_artists(self):
        title, artist = parse_title_artist(
            "track - Subtronics Remix",
            [{"name": "Subtronics"}, {"name": "Other"}],
        )
        assert title == "track (Subtronics Remix)"
        assert artist == "Subtronics, Other"

    def test_multiple_dashes_only_first_split(self):
        title, artist = parse_title_artist(
            "Artist - Song Title - Extended Mix (DJ Remix)",
            [{"name": "Channel"}],
        )
        assert title == "Song Title - Extended Mix (DJ Remix)"
        assert artist == "Artist, DJ"

    def test_bare_remix_ampersand_remixers(self):
        title, artist = parse_title_artist(
            "track - A & B Remix",
            [{"name": "Original"}],
        )
        assert title == "track (A & B Remix)"
        assert artist == "Original, A, B"

    def test_no_dash_remix_with_ampersand_artists(self):
        """No dash in title — preserve structured artist name and extract remixers."""
        title, artist = parse_title_artist(
            "Go Back (YDG Remix) (feat. Julia Church)",
            [{"name": "John Summit & Sub Focus"}],
        )
        assert title == "Go Back (YDG Remix) (feat. Julia Church)"
        assert artist == "John Summit & Sub Focus, YDG"


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
