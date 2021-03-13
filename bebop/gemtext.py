"""Gemtext parser.

To allow a flexible rendering of the content, the parser produces a list of
"elements", each being an instance of one of the dataclasses defined in this
module. A renderer can then completely abstract the original document.
"""

import re
from dataclasses import dataclass
from typing import List


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


def parse_gemtext(text: str):
    """Parse a string of Gemtext into a list of elements."""
    elements = []
    preformatted = None
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue

        match = Title.RE.match(line)
        if match:
            hashtags, text = match.groups()
            elements.append(Title(hashtags.count("#"), text))
            continue

        match = Link.RE.match(line)
        if match:
            match_dict = match.groupdict()
            url, text = match_dict["url"], match_dict.get("text", "")
            elements.append(Link(url, text))
            continue

        if line.startswith(Preformatted.FENCE):
            if preformatted:
                elements.append(preformatted)
                preformatted = None
            else:
                preformatted = Preformatted([])
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

        if preformatted:
            preformatted.lines.append(line)
        else:
            elements.append(Paragraph(line))

    # If a preformatted block is not closed before the file ends, consider it
    # closed anyway; the spec does not seem to talk about that case.
    if preformatted:
        elements.append(preformatted)

    return elements
