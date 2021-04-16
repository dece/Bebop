from dataclasses import dataclass, field

from bebop.gemtext import parse_gemtext, Title
from bebop.metalines import generate_dumb_metalines, generate_metalines
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
    """
    source: str
    metalines: list = field(default_factory=list)
    links: Links = field(default_factory=Links)
    title: str = ""

    @staticmethod
    def from_gemtext(gemtext: str):
        """Produce a Page from a Gemtext file or string."""
        elements, links, title = parse_gemtext(gemtext)
        metalines = generate_metalines(elements, 80)
        return Page(gemtext, metalines, links, title)

    @staticmethod
    def from_text(text: str):
        """Produce a Page for a text string."""
        metalines = generate_dumb_metalines(text.splitlines())
        return Page(text, metalines)
