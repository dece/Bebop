import curses
import string
from enum import IntEnum

from bebop.colors import ColorPair
from bebop.gemtext import (Blockquote, Link, ListItem, Paragraph, Preformatted,
    Title)


SPLIT_CHARS = " \t-"
JOIN_CHAR = "-"
LIST_ITEM_MARK = "• "


class LineType(IntEnum):
    """Type of line.

    Keep lines type along with the content for later rendering.
    Title type values match the title level to avoid looking it up.
    """
    NONE = 0
    TITLE_1 = 1
    TITLE_2 = 2
    TITLE_3 = 3
    PARAGRAPH = 4
    LINK = 5
    PREFORMATTED = 6
    BLOCKQUOTE = 7
    LIST_ITEM = 8


def format_elements(elements, width):
    """Format elements into a list of lines with metadata.

    The returned list ("metalines") are tuples (meta, line), meta being a
    dict of metadata and line a text line to display. Currently the only
    metadata keys used are:
    - type: one of the Renderer.TYPE constants.
    - url: only for links, the URL the link on this line refers to. Note
      that this key is present only for the first line of the link, i.e.
      long link descriptions wrapped on multiple lines will not have a this
      key except for the first line.
    - link_id: only alongside "url" key, ID generated for this link.
    """
    metalines = []
    context = {"last_link_id": 0, "width": width}
    separator = ({"type": LineType.NONE}, "")
    has_margins = False
    for index, element in enumerate(elements):
        previous_had_margins = has_margins
        has_margins = False
        if isinstance(element, Title):
            element_metalines = format_title(element, context)
            has_margins = True
        elif isinstance(element, Paragraph):
            element_metalines = format_paragraph(element, context)
            has_margins = True
        elif isinstance(element, Link):
            element_metalines = format_link(element, context)
        elif isinstance(element, Preformatted):
            element_metalines = format_preformatted(element, context)
            has_margins = True
        elif isinstance(element, Blockquote):
            element_metalines = format_blockquote(element, context)
            has_margins = True
        elif isinstance(element, ListItem):
            element_metalines = format_list_item(element, context)
        else:
            continue
        # If current element requires margins and is not the first elements,
        # separate from previous element. Also do it if the current element does
        # not require margins but follows an element that required it (e.g. link
        # after a paragraph).
        if (
            (has_margins and index > 0)
            or (not has_margins and previous_had_margins)
        ):
            metalines.append(separator)
        metalines += element_metalines
    return metalines


def format_title(title: Title, context: dict):
    """Return metalines for this title."""
    if title.level == 1:
        wrapped = wrap_words(title.text, context["width"])
        line_template = f"{{:^{context['width']}}}"
        lines = (line_template.format(line) for line in wrapped)
    else:
        if title.level == 2:
            lines = wrap_words(title.text, context["width"], indent=2)
        else:
            lines = wrap_words(title.text, context["width"])
    # Title levels match the type constants of titles.
    return [({"type": LineType(title.level)}, line) for line in lines]


def format_paragraph(paragraph: Paragraph, context: dict):
    """Return metalines for this paragraph."""
    lines = wrap_words(paragraph.text, context["width"])
    return [({"type": LineType.PARAGRAPH}, line) for line in lines]


def format_link(link: Link, context: dict):
    """Return metalines for this link."""
    # Get a new link and build the "[id]" anchor.
    link_id = context["last_link_id"] + 1
    context["last_link_id"] = link_id
    link_text = link.text or link.url
    link_anchor = f"[{link_id}] "
    # Wrap lines, indented by the link anchor length.
    lines = wrap_words(link_text, context["width"], indent=len(link_anchor))
    first_line_meta = {
        "type": LineType.LINK,
        "url": link.url,
        "link_id": link_id
    }
    # Replace first line indentation with the anchor.
    first_line_text = link_anchor + lines[0][len(link_anchor):]
    first_line = [(first_line_meta, first_line_text)]
    other_lines = [({"type": LineType.LINK}, line) for line in lines[1:]]
    return first_line + other_lines


def format_preformatted(preformatted: Preformatted, context: dict):
    """Return metalines for this preformatted block."""
    return [
        ({"type": LineType.PREFORMATTED}, line)
        for line in preformatted.lines
    ]


def format_blockquote(blockquote: Blockquote, context: dict):
    """Return metalines for this blockquote."""
    lines = wrap_words(blockquote.text, context["width"])
    return [({"type": LineType.BLOCKQUOTE}, line) for line in lines]


def format_list_item(item: ListItem, context: dict):
    """Return metalines for this list item."""
    indent = len(LIST_ITEM_MARK)
    lines = wrap_words(item.text, context["width"], indent=indent)
    first_line = LIST_ITEM_MARK + lines[0][indent:]
    lines[0] = first_line
    return [({"type": LineType.LIST_ITEM}, line) for line in lines]


def wrap_words(text, width, indent=0):
    """Wrap a text in several lines according to the renderer's width."""
    lines = []
    line = " " * indent
    words = _explode_words(text)
    for word in words:
        line_len, word_len = len(line), len(word)
        # If adding the new word would overflow the line, use a new line.
        if line_len + word_len > width:
            # Push only non-empty lines.
            if line_len > 0:
                lines.append(line)
                line = " " * indent
            # Force split words that are longer than the width.
            while word_len > width:
                split_offset = width - 1 - indent
                word_line = " " * indent + word[:split_offset] + JOIN_CHAR
                lines.append(word_line)
                word = word[split_offset:]
                word_len = len(word)
            word = word.lstrip()
        line += word
    if line:
        lines.append(line)
    return lines


def _explode_words(text):
    words = []
    pos = 0
    while True:
        sep, sep_index = _find_next_sep(text[pos:])
        if not sep:
            words.append(text[pos:])
            return words
        word = text[pos : pos + sep_index]
        # If the separator is not a space char, append it to the word.
        if sep in string.whitespace:
            words.append(word)
            words.append(sep)
        else:
            words.append(word + sep)
        pos += sep_index + 1


def _find_next_sep(text):
    indices = []
    for sep in SPLIT_CHARS:
        try:
            indices.append((sep, text.index(sep)))
        except ValueError:
            pass
    if not indices:
        return ("", 0)
    return min(indices, key=lambda e: e[1])


def render_lines(metalines, window, max_width):
    """Write a list of metalines in window.

    As this function does not know about the window/pad previous size, it
    expects a cleared window, especially if the new content is shorter than the
    previous one: merely clearing after the resize will not remove artefacts.

    Arguments:
    - metalines: list of metalines to render, must have at least one element.
    - window: window that will be resized as filled with rendered lines.
    - max_width: line length limit for the pad.

    Return:
    The tuple of integers (error, height, width), error being a non-zero value
    if an error occured during rendering, and height and width being the new
    dimensions of the resized window.
    """
    num_lines = len(metalines)
    new_dimensions = num_lines, max_width
    window.resize(*new_dimensions)
    for line_index, metaline in enumerate(metalines):
        try:
            render_line(metaline, window, max_width)
        except ValueError:
            return new_dimensions
        if line_index < num_lines - 1:
            window.addstr("\n")
    return new_dimensions


def render_line(metaline, window, max_width):
    """Write a single line to the window."""
    meta, line = metaline
    line_type = meta["type"]
    attributes = get_base_line_attributes(line_type)
    line = line[:max_width - 1]
    window.addstr(line, attributes)
    if meta["type"] == LineType.LINK and "url" in meta:
        url_text = f' - {meta["url"]}'
        attributes = (
            curses.color_pair(ColorPair.LINK_PREVIEW)
            | curses.A_DIM
            | curses.A_ITALIC
        )
        window.addstr(url_text, attributes)


def get_base_line_attributes(line_type):
    """Return the base attributes for this line type.

    Other attributes may be freely used later for this line type but this is
    what is used at the start of most lines of the given type.
    """
    if line_type == LineType.TITLE_1:
        return curses.color_pair(ColorPair.TITLE_1) | curses.A_BOLD
    elif line_type == LineType.TITLE_2:
        return curses.color_pair(ColorPair.TITLE_2) | curses.A_BOLD
    elif line_type == LineType.TITLE_3:
        return curses.color_pair(ColorPair.TITLE_3)
    elif line_type == LineType.LINK:
        return curses.color_pair(ColorPair.LINK)
    elif line_type == LineType.PREFORMATTED:
        return curses.color_pair(ColorPair.PREFORMATTED)
    elif line_type == LineType.BLOCKQUOTE:
        return curses.color_pair(ColorPair.BLOCKQUOTE) | curses.A_ITALIC
    else:  # includes LineType.PARAGRAPH
        return curses.color_pair(ColorPair.NORMAL)
