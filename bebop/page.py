from dataclasses import dataclass, field

from bebop.gemtext import parse_gemtext, Title
from bebop.metalines import generate_metalines
from bebop.links import Links


@dataclass
class Page:
    """Page-related data.

    Attributes:
    - metalines: lines ready to be rendered.
    - links: Links instance, mapping IDs to links on the page; this data is
      redundant as the links' URLs/IDs are already available in the
      corresponding metalines, it is meant to be used as a quick map for link ID
      lookup and disambiguation.
    - title: optional page title.
    """
    metalines: list = field(default_factory=list)
    links: Links = field(default_factory=Links)
    title: str = ""

    @staticmethod
    def from_gemtext(gemtext: str):
        """Produce a Page from a Gemtext file or string."""
        elements, links, title = parse_gemtext(gemtext)
        metalines = generate_metalines(elements, 80)
        return Page(metalines, links, title)
