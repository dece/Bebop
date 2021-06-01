import unittest

from ..mime import MimeType


class TestMime(unittest.TestCase):

    def test_from_str(self):
        self.assertIsNone(MimeType.from_str(""))
        self.assertIsNone(MimeType.from_str("dumb"))
        self.assertIsNone(MimeType.from_str("dumb;dumber"))
        self.assertIsNone(MimeType.from_str("123456"))

        mime = MimeType.from_str("a/b")
        self.assertEqual(mime.main_type, "a")
        self.assertEqual(mime.sub_type, "b")
        self.assertEqual(mime.parameters, {})

        mime = MimeType.from_str("text/gemini")
        self.assertEqual(mime.main_type, "text")
        self.assertEqual(mime.sub_type, "gemini")
        self.assertEqual(mime.parameters, {})

        mime = MimeType.from_str("text/gemini;lang=en")
        self.assertEqual(mime.main_type, "text")
        self.assertEqual(mime.sub_type, "gemini")
        self.assertEqual(mime.parameters, {"lang": "en"})
        mime = MimeType.from_str("text/gemini ;lang=en")
        self.assertEqual(mime.parameters, {"lang": "en"})
