import unittest

from ..protocol import parse_gemini_url


class TestGemini(unittest.TestCase):

    def test_parse_url(self):
        r1 = parse_gemini_url("gemini://dece.space")
        self.assertDictEqual(r1, {"host": "dece.space", "path": ""})
