"""Gemtext parser.

To allow a flexible rendering of the content, the parser produces a list of
"elements", each being an instance of one of the dataclasses defined in this
module. A renderer can then completely abstract the original document.
"""

import re
from collections import namedtuple
from dataclasses import dataclass
from typing import List

from bebop.links import Links


@dataclass
class Paragraph:
    text: str


@dataclass
class Title:
    level: int
    text: str
    RE = re.compile(r"(#{1,3})\s+(.+)")


@dataclass
class Link:
    url: str
    text: str
    ident: int = 0
    RE = re.compile(r"=>\s*(?P<url>\S+)(\s+(?P<text>.+))?")


@dataclass
class Preformatted:
    lines: List[str]
    FENCE = "```"


@dataclass
class Blockquote:
    text: str
    RE = re.compile(r">\s*(.*)")


@dataclass
class ListItem:
    text: str
    RE = re.compile(r"\*\s(.*)")


ParsedGemtext = namedtuple("ParsedGemtext", ("elements", "links", "title"))


def parse_gemtext(text: str, dumb=False) -> ParsedGemtext:
    """Parse a string of Gemtext into a list of elements."""
    elements = []
    links = Links()
    last_link_id = 0
    title = ""
    preformatted = None
    for line in text.splitlines():
        line = line.rstrip()
        # Empty lines:
        # - in standard mode, discard them, except for preformatted blocks.
        # - in dumb mode, keep them.
        if not line and not (dumb or preformatted):
            continue

        if line.startswith(Preformatted.FENCE):
            if preformatted:
                elements.append(preformatted)
                preformatted = None
            else:
                preformatted = Preformatted([])
            continue

        if preformatted:
            preformatted.lines.append(line)
            continue

        match = Title.RE.match(line)
        if match:
            hashtags, text = match.groups()
            level = hashtags.count("#")
            elements.append(Title(level, text))
            if not title and level == 1:
                title = text
            continue

        match = Link.RE.match(line)
        if match:
            match_dict = match.groupdict()
            url, text = match_dict["url"], match_dict.get("text", "")
            last_link_id += 1
            links[last_link_id] = url
            elements.append(Link(url, text, last_link_id))
            continue

        match = Blockquote.RE.match(line)
        if match:
            text = match.groups()[0]
            elements.append(Blockquote(text))
            continue

        match = ListItem.RE.match(line)
        if match:
            text = match.groups()[0]
            elements.append(ListItem(text))
            continue

        elements.append(Paragraph(line))

    # If a preformatted block is not closed before the file ends, consider it
    # closed anyway; the spec does not seem to talk about that case.
    if preformatted:
        elements.append(preformatted)

    return ParsedGemtext(elements, links, title)
