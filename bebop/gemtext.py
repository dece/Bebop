import re
import typing
from dataclasses import dataclass


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
    lines: typing.List[str]
    FENCE = "```"


@dataclass
class Blockquote:
    text: str
    RE = re.compile(r">\s*(.*)")


def parse_gemtext(data):
    """Parse UTF-8 encoded Gemtext as a list of elements."""
    text = data.decode(encoding="utf8", errors="ignore")
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

        if line == Preformatted.FENCE:
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

        if preformatted:
            preformatted.lines.append(line)
        else:
            elements.append(Paragraph(line))

    return elements
