"""Rendering Gemtext in curses."""

import curses

from bebop.colors import ColorPair
from bebop.metalines import LineType


def render_lines(metalines, window, max_width):
    """Write a list of metalines in window.

    As this function does not know about the window/pad previous size, it
    expects a cleared window, especially if the new content is shorter than the
    previous one: merely clearing after the resize will not remove artefacts.

    Arguments:
    - metalines: list of metalines to render, must have at least one element.
    - window: window that will be resized as filled with rendered lines.
    - max_width: line length limit for the pad.

    Returns:
    The tuple of integers (error, height, width), error being a non-zero value
    if an error occured during rendering, and height and width being the new
    dimensions of the resized window.
    """
    num_lines = len(metalines)
    new_dimensions = max(num_lines, 1), max_width
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
        url_text = f'  {meta["url"]}'
        attributes = (
            curses.color_pair(ColorPair.LINK_PREVIEW)
            | curses.A_DIM
            | curses.A_ITALIC
        )
        window.addstr(url_text, attributes)


def get_base_line_attributes(line_type) -> int:
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
