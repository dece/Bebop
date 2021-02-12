import unittest

from ..navigation import join_url, parse_url


class TestNavigation(unittest.TestCase):

    def test_parse_url(self):
        res = parse_url("gemini://dece.space/parse-me.gmi")
        self.assertEqual(res.scheme, "gemini")
        self.assertEqual(res.netloc, "dece.space")
        self.assertEqual(res.path, "/parse-me.gmi")

        res_netloc = parse_url("//dece.space/parse-me.gmi")
        self.assertEqual(res, res_netloc)

        res = parse_url("dece.space/parse-me.gmi", absolute=True)
        self.assertEqual(res.scheme, "gemini")
        self.assertEqual(res.netloc, "dece.space")
        self.assertEqual(res.path, "/parse-me.gmi")

    def test_join_url(self):
        url = join_url("gemini://dece.space", "some-file.gmi")
        self.assertEqual(url, "gemini://dece.space/some-file.gmi")
        url = join_url("gemini://dece.space", "some-file.gmi")
        self.assertEqual(url, "gemini://dece.space/some-file.gmi")
        url = join_url("gemini://dece.space/dir1/file.gmi", "other-file.gmi")
        self.assertEqual(url, "gemini://dece.space/dir1/other-file.gmi")
        url = join_url("gemini://dece.space/dir1/file.gmi", "../top-level.gmi")
        self.assertEqual(url, "gemini://dece.space/top-level.gmi")
