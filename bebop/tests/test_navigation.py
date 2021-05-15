import unittest

from ..navigation import (
    get_parent_url, get_root_url, join_url, parse_url, pop_first_segment, remove_dot_segments,
    remove_last_segment, set_parameter,
)


class TestNavigation(unittest.TestCase):

    def test_parse_url(self):
        # Basic complete URL.
        res = parse_url("gemini://netloc/parse-me.gmi")
        self.assertEqual(res["scheme"], "gemini")
        self.assertEqual(res["netloc"], "netloc")
        self.assertEqual(res["path"], "/parse-me.gmi")

        # No scheme.
        res_netloc = parse_url("//netloc/parse-me.gmi")
        self.assertIsNone(res_netloc["scheme"], None)
        for key in res_netloc:
            if key == "scheme":
                continue
            self.assertEqual(res_netloc[key], res[key])

        # No scheme but a default is provided.
        res_netloc = parse_url("//netloc/parse-me.gmi", default_scheme="gemini")
        self.assertDictEqual(res_netloc, res)

        # No scheme nor netloc: only a path should be produced.
        res = parse_url("dece.space/parse-me.gmi")
        self.assertIsNone(res["scheme"])
        self.assertIsNone(res["netloc"])
        self.assertEqual(res["path"], "dece.space/parse-me.gmi")

        # No scheme nor netloc but we should pretend having an absolute URL.
        res = parse_url("dece.space/parse-me.gmi", absolute=True)
        self.assertIsNone(res["scheme"])
        self.assertEqual(res["netloc"], "dece.space")
        self.assertEqual(res["path"], "/parse-me.gmi")

        # HTTPS scheme.
        res = parse_url("https://dece.space/index.html")
        self.assertEqual(res["scheme"], "https")
        self.assertEqual(res["netloc"], "dece.space")
        self.assertEqual(res["path"], "/index.html")

        # File scheme.
        res = parse_url("file:///home/dece/gemini/index.gmi")
        self.assertEqual(res["scheme"], "file")
        self.assertEqual(res["path"], "/home/dece/gemini/index.gmi")

        # Bebop scheme.
        res = parse_url("bebop:welcome")
        self.assertEqual(res["scheme"], "bebop")
        self.assertIsNone(res["netloc"])
        self.assertEqual(res["path"], "welcome")

    def test_join_url(self):
        url = join_url("gemini://dece.space/", "some-file.gmi")
        self.assertEqual(url, "gemini://dece.space/some-file.gmi")
        url = join_url("gemini://dece.space/", "./some-file.gmi")
        self.assertEqual(url, "gemini://dece.space/some-file.gmi")
        url = join_url("gemini://dece.space/dir1", "/some-file.gmi")
        self.assertEqual(url, "gemini://dece.space/some-file.gmi")
        url = join_url("gemini://dece.space/dir1/file.gmi", "other-file.gmi")
        self.assertEqual(url, "gemini://dece.space/dir1/other-file.gmi")
        url = join_url("gemini://dece.space/dir1/file.gmi", "../top-level.gmi")
        self.assertEqual(url, "gemini://dece.space/top-level.gmi")
        url = join_url("s://hard/dir/a", "./../test/b/c/../d/e/f/../.././a.gmi")
        self.assertEqual(url, "s://hard/test/b/d/a.gmi")

    def test_remove_dot_segments(self):
        paths = [
            ("index.gmi", "index.gmi"),
            ("/index.gmi", "/index.gmi"),
            ("./index.gmi", "index.gmi"),
            ("/./index.gmi", "/index.gmi"),
            ("/../index.gmi", "/index.gmi"),
            ("/a/b/c/./../../g", "/a/g"),
            ("mid/content=5/../6", "mid/6"),
            ("../../../../g", "g"),
        ]
        for path, expected in paths:
            self.assertEqual(
                remove_dot_segments(path),
                expected,
                msg="path was " + path
            )

    def test_remove_last_segment(self):
        self.assertEqual(remove_last_segment(""), "")
        self.assertEqual(remove_last_segment("/"), "")
        self.assertEqual(remove_last_segment("/a"), "")
        self.assertEqual(remove_last_segment("/a/"), "/a")
        self.assertEqual(remove_last_segment("/a/b"), "/a")
        self.assertEqual(remove_last_segment("/a/b/c/d"), "/a/b/c")
        self.assertEqual(remove_last_segment("///"), "//")

    def test_pop_first_segment(self):
        self.assertEqual(pop_first_segment(""), ("", ""))
        self.assertEqual(pop_first_segment("a"), ("a", ""))
        self.assertEqual(pop_first_segment("/a"), ("/a", ""))
        self.assertEqual(pop_first_segment("/a/"), ("/a", "/"))
        self.assertEqual(pop_first_segment("/a/b"), ("/a", "/b"))
        self.assertEqual(pop_first_segment("a/b"), ("a", "/b"))

    def test_set_parameter(self):
        url = set_parameter("gemini://gus.guru/search", "my search")
        self.assertEqual(url, "gemini://gus.guru/search?my%20search")
        url = set_parameter("gemini://gus.guru/search?old%20search", "new")
        self.assertEqual(url, "gemini://gus.guru/search?new")

    def test_get_parent_url(self):
        urls_and_parents = [
            ("gemini://host", "gemini://host"),
            ("gemini://host/", "gemini://host/"),
            ("gemini://host/a", "gemini://host/"),
            ("gemini://host/a/", "gemini://host/"),
            ("gemini://host/a/index.gmi", "gemini://host/a/"),
            ("gemini://host/a/b/", "gemini://host/a/"),
            ("gemini://host/a/b/file.flac", "gemini://host/a/b/"),
            ("//host/a/b", "//host/a/"),
            ("hey", "hey"),  # does not really make sense but whatever
            ("hey/ho", "hey/"),
            ("hey/ho/letsgo", "hey/ho/"),
        ]
        for url, parent in urls_and_parents:
            self.assertEqual(
                get_parent_url(url),
                parent,
                msg="URL was " + url)

    def test_get_root_url(self):
        urls_and_roots = [
            ("gemini://host", "gemini://host/"),
            ("gemini://host/", "gemini://host/"),
            ("gemini://host/a", "gemini://host/"),
            ("gemini://host/a/b/c", "gemini://host/"),
            ("//host/path", "//host/"),
            ("//host/path?query", "//host/"),
            ("dumb", "/"),
            ("dumb/dumber", "/"),
        ]
        for url, root in urls_and_roots:
            self.assertEqual(
                get_root_url(url), 
                root, 
                msg="URL was " + url
            )
