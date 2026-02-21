"""Tests for likedmusic.sync_engine — _sanitize_filename."""

from likedmusic.sync_engine import _sanitize_filename


class TestSanitizeFilename:
    def test_removes_invalid_chars(self):
        assert _sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_preserves_unicode(self):
        assert _sanitize_filename("cafe\u0301") == "cafe\u0301"

    def test_empty_string(self):
        assert _sanitize_filename("") == ""

    def test_no_invalid_chars(self):
        assert _sanitize_filename("normal filename") == "normal filename"

    def test_long_name(self):
        long_name = "a" * 300
        result = _sanitize_filename(long_name)
        assert result == long_name  # sanitize doesn't truncate, just removes bad chars
