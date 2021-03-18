from dataclasses import dataclass, field

from bebop.gemtext import parse_gemtext, Title
from bebop.rendering import generate_metalines
from bebop.links import Links


@dataclass
class Page:
    """Page-related data."""
    metalines: list = field(default_factory=list)
    links: Links = field(default_factory=Links)
    title: str = ""

    @staticmethod
    def from_gemtext(gemtext: str):
        """Produce a Page from a Gemtext file or string."""
        elements = parse_gemtext(gemtext)
        metalines = generate_metalines(elements, 80)
        links = Links.from_metalines(metalines)
        # TODO this is horrible; merge parsing with page generation directly
        title = ""
        for element in elements:
            if isinstance(element, Title) and element.level == 1:
                title = element.text
                break
        return Page(metalines, links, title)
