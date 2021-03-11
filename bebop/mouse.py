"""Mouse support utilities."""

from enum import IntEnum


class ButtonState(IntEnum):
    """Most common flags from curses.getmouse()'s bstate.

    Could not find a clear reference for that and released/pressed seem inverted
    compared to snippets on the Web, so take portability with a grain of salt.
    """
    LEFT_RELEASED = 1 << 0
    LEFT_PRESSED  = 1 << 1
    LEFT_CLICKED  = 1 << 2
    LEFT_DCLICKED = 1 << 3
    LEFT_TCLICKED = 1 << 4
    MIDDLE_RELEASED = 1 << 5
    MIDDLE_PRESSED  = 1 << 6
    MIDDLE_CLICKED  = 1 << 7
    MIDDLE_DCLICKED = 1 << 8
    MIDDLE_TCLICKED = 1 << 9
    RIGHT_RELEASED = 1 << 10
    RIGHT_PRESSED  = 1 << 11
    RIGHT_CLICKED  = 1 << 12
    RIGHT_DCLICKED = 1 << 13
    RIGHT_TCLICKED = 1 << 14
    SCROLL_UP      = 1 << 16
    SCROLL_DOWN    = 1 << 21
    SHIFT          = 1 << 25
    CTRL           = 1 << 26
