"""Color definitions for curses."""

import curses
from enum import IntEnum


class ColorPair(IntEnum):
    # Colors for specific Gemtext line type.
    NORMAL       = 0
    ERROR        = 1
    LINK         = 2
    LINK_ID      = 3
    TITLE_1      = 4
    TITLE_2      = 5
    TITLE_3      = 6
    PREFORMATTED = 7
    BLOCKQUOTE   = 8

    # Colors for other usage in the browser.
    LINK_PREVIEW = 9
    DEBUG        = 99


def init_colors():
    curses.use_default_colors()
    curses.init_pair(ColorPair.NORMAL, curses.COLOR_WHITE, -1)
    curses.init_pair(ColorPair.ERROR, curses.COLOR_RED, -1)
    curses.init_pair(ColorPair.LINK, curses.COLOR_CYAN, -1)
    curses.init_pair(ColorPair.LINK_ID, curses.COLOR_WHITE, -1)
    curses.init_pair(ColorPair.TITLE_1, curses.COLOR_GREEN, -1)
    curses.init_pair(ColorPair.TITLE_2, curses.COLOR_MAGENTA, -1)
    curses.init_pair(ColorPair.TITLE_3, curses.COLOR_MAGENTA, -1)
    curses.init_pair(ColorPair.PREFORMATTED, curses.COLOR_YELLOW, -1)
    curses.init_pair(ColorPair.BLOCKQUOTE, curses.COLOR_CYAN, -1)
    curses.init_pair(ColorPair.LINK_PREVIEW, curses.COLOR_WHITE, -1)
    curses.init_pair(ColorPair.DEBUG, curses.COLOR_BLACK, curses.COLOR_GREEN)
