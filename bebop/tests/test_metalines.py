import unittest

from ..metalines import _explode_words, _find_next_sep, wrap_words


class TestMetalines(unittest.TestCase):

    def test_wrap_words(self):
        t = "wrap me wrap me youcantwrapthisonewithoutforce bla bla bla bla"
        lines = wrap_words(t, 10)
        expected = [
            "wrap me ",
            "wrap me ",
            "youcantwr-",
            "apthisone-",
            "withoutfo-",
            "rce bla ",
            "bla bla ",
            "bla",
        ]
        self.assertListEqual(lines, expected)

    def test_explode_words(self):
        t = "unsplittableword word-dash	tabatmyleft dot.sep"
        words = _explode_words(t)
        expected = [
            "unsplittableword", " ", "word-", "dash", "	", "tabatmyleft",
            " ", "dot.sep"
        ]
        self.assertListEqual(words, expected)

    def test_find_next_sep(self):
        t = "unsplittableword word-dash"
        sep, index = _find_next_sep(t)
        self.assertEqual((sep, index), (" ", 16))
        t = t[17:]
        sep, index = _find_next_sep(t)
        self.assertEqual((sep, index), ("-", 4))
        t = t[5:]
        sep, index = _find_next_sep(t)
        self.assertEqual((sep, index), ("", 0))
