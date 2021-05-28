from dataclasses import dataclass, field
from typing import Optional

from bebop.gemtext import parse_gemtext
from bebop.metalines import generate_dumb_metalines, generate_metalines
from bebop.mime import MimeType
from bebop.links import Links


@dataclass
class Page:
    """Page-related data.

    Attributes:
    - source: str used to create the page.
    - metalines: lines ready to be rendered.
    - links: Links instance, mapping IDs to links on the page; this data is
      redundant as the links' URLs/IDs are already available in the
      corresponding metalines, it is meant to be used as a quick map for link ID
      lookup and disambiguation.
    - title: optional page title.
    - mime: optional MIME type received from the server.
    - encoding: optional encoding received from the server.
    - render: optional render mode used to create the page from Gemtext.
    """
    source: str
    metalines: list = field(default_factory=list)
    links: Links = field(default_factory=Links)
    title: str = ""
    mime: Optional[MimeType] = None
    encoding: str = ""
    render: Optional[str] = None

    @staticmethod
    def from_gemtext(gemtext: str, wrap_at: int, render: str ="fancy"):
        """Produce a Page from a Gemtext file or string."""
        dumb_mode = render == "dumb"
        elements, links, title = parse_gemtext(gemtext, dumb=dumb_mode)
        metalines = generate_metalines(elements, wrap_at, dumb=dumb_mode)
        return Page(gemtext, metalines, links, title, render=render)

    @staticmethod
    def from_text(text: str):
        """Produce a Page for a text string."""
        metalines = generate_dumb_metalines(text.splitlines())
        return Page(text, metalines)
