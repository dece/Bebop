import unittest

from ..preferences import get_url_render_mode_pref

class TestPreferences(unittest.TestCase):

    def test_get_url_render_mode_pref(self):
        prefs = {}
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com",
            "default"
        ), "default")

        prefs["gemini://example.com"] = {}
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com",
            "default"
        ), "default")

        prefs["gemini://example.com"] = {"render_mode": "test"}
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com",
            "default"
        ), "test")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/path",
            "default"
        ), "test")

        prefs["gemini://example.com/specific/subdir"] = {"render_mode": "test2"}
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/path",
            "default"
        ), "test")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/specific",
            "default"
        ), "test")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/specific/subdir",
            "default"
        ), "test2")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/specific/subdir/subsubdir",
            "default"
        ), "test2")
