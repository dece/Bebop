from bebop.metalines import RenderOptions
import unittest

from ..external import substitute_external_command
from ..page import Page


URL = "gemini://example.com"
GEMTEXT = """\
# Test page

Blablabla

=> gemini://example.com/index.gmi Link to index
=> gemini://example.com/sub/gemlog.gmi Link to gemlog
"""
PAGE = Page.from_gemtext(GEMTEXT, RenderOptions(80, "fancy", "- "))


class TestExternal(unittest.TestCase):

    def test_substitute_external_command(self):
        # Replace URLs occurences.
        command = "gmni $u | grep $u"  # Grep for a page's own URL.
        result = substitute_external_command(command, URL, PAGE)
        self.assertEqual(result, "gmni {u} | grep {u}".format(u=URL))

        # Replace link ID's with the target URL.
        command = "gmni $1 && gmni $2"  # Get both links
        result = substitute_external_command(command, URL, PAGE)
        expected = (
            "gmni gemini://example.com/index.gmi"
            " && gmni gemini://example.com/sub/gemlog.gmi"
        )
        self.assertEqual(result, expected)

        # Invalid link ID raise a ValueError.
        command = "gmni $8"
        with self.assertRaises(Exception):
            substitute_external_command(command, URL, PAGE)

        # Replace escaped $$ with literal $.
        command = "grep ^iamaregex$$ | echo dollar $"  # Do nothing with last.
        result = substitute_external_command(command, URL, PAGE)
        self.assertEqual(result, "grep ^iamaregex$ | echo dollar $")
