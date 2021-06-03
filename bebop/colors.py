"""Color definitions for curses."""

import curses
import logging
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
    DEBUG        = 9
    LINK_PREVIEW = 10


A_ITALIC = curses.A_ITALIC if hasattr(curses, "A_ITALIC") else curses.A_NORMAL


def init_colors(bg: int =-1):
    curses.use_default_colors()
    curses.init_pair(ColorPair.DEBUG, curses.COLOR_BLACK, curses.COLOR_GREEN)
    try:
        curses.init_pair(ColorPair.NORMAL, curses.COLOR_WHITE, bg)
        curses.init_pair(ColorPair.ERROR, curses.COLOR_RED, bg)
        curses.init_pair(ColorPair.LINK, curses.COLOR_CYAN, bg)
        curses.init_pair(ColorPair.LINK_ID, curses.COLOR_WHITE, bg)
        curses.init_pair(ColorPair.TITLE_1, curses.COLOR_GREEN, bg)
        curses.init_pair(ColorPair.TITLE_2, curses.COLOR_MAGENTA, bg)
        curses.init_pair(ColorPair.TITLE_3, curses.COLOR_MAGENTA, bg)
        curses.init_pair(ColorPair.PREFORMATTED, curses.COLOR_YELLOW, bg)
        curses.init_pair(ColorPair.BLOCKQUOTE, curses.COLOR_BLUE, bg)
        curses.init_pair(ColorPair.LINK_PREVIEW, curses.COLOR_WHITE, bg)
    except curses.error:
        logging.error("Failed to init colors.")
        if bg == -1:
            logging.debug("Retrying with black background…")
            init_colors(bg=curses.COLOR_BLACK)
