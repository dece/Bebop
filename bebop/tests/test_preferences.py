import unittest

from ..preferences import get_url_render_mode_pref

class TestPreferences(unittest.TestCase):

    def test_get_url_render_mode_pref(self):
        prefs = {}
        self.assertIsNone(get_url_render_mode_pref(
            prefs,
            "gemini://example.com",
        ))

        prefs["gemini://example.com"] = {}
        self.assertIsNone(get_url_render_mode_pref(
            prefs,
            "gemini://example.com",
        ))

        prefs["gemini://example.com"] = {"render_mode": "test"}
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com",
        ), "test")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/path",
        ), "test")

        prefs["gemini://example.com/specific/subdir"] = {"render_mode": "test2"}
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/path",
        ), "test")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/specific",
        ), "test")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/specific/subdir",
        ), "test2")
        self.assertEqual(get_url_render_mode_pref(
            prefs,
            "gemini://example.com/specific/subdir/subsubdir",
        ), "test2")
