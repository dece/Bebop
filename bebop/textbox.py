"""Fork of Python's standard library curses.textpad module.

I guess it requires some license header?

Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011,
2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021
Python Software Foundation;
All Rights Reserved

This version fixes a few quirks of the standard module, namely:

- Discard multi-lines mode: only one line is supported.
"""

import curses
import curses.ascii
import logging


class Textbox:
    """Editing widget using the interior of a window object.

    - Ctrl-A: Go to left edge of window.
    - Ctrl-B: Cursor left, wrapping to previous line if appropriate.
    - Ctrl-D: Delete character under cursor.
    - Ctrl-E: Go to right edge (stripspaces off) or end of line (stripspaces on).
    - Ctrl-F: Cursor right, wrapping to next line when appropriate.
    - Ctrl-H: Delete character backward.
    - Ctrl-K: If line is blank, delete it, otherwise clear to end of line.
    - Ctrl-L: Refresh screen.

    Move operations do nothing if the cursor is at an edge where the movement
    is not possible.  The following synonyms are supported where possible:

    - KEY_LEFT: Ctrl-B
    - KEY_RIGHT: Ctrl-F
    - KEY_UP: Ctrl-P
    - KEY_DOWN: Ctrl-N
    - KEY_BACKSPACE: Ctrl-H
    """
    def __init__(self, win, insert_mode=False):
        self.win = win
        self.insert_mode = insert_mode
        self._update_maxx()
        self.stripspaces = True
        win.keypad(1)

    def _update_maxx(self):
        _, maxx = self.win.getmaxyx()
        self.maxx = maxx - 1

    def _end_of_line(self):
        """Return the index of the last non-blank character."""
        logging.debug(f"textpad._end_of_line")
        self._update_maxx()
        last = self.maxx
        while True:
            last_ch = curses.ascii.ascii(self.win.inch(0, last))
            if last_ch != curses.ascii.SP:
                last = min(self.maxx, last + 1)
                break
            elif last == 0:
                break
            last = last - 1
        return last

    def _insert_printable_char(self, ch):
        logging.debug(f"textpad._insert_printable_char {ch}")
        self._update_maxx()
        _, x = self.win.getyx()
        backx = None
        while x < self.maxx:
            oldch = 0
            if self.insert_mode:
                oldch = self.win.inch()
            # The try-catch ignores the error we trigger from some curses
            # versions by trying to write into the lowest-rightmost spot
            # in the window.
            try:
                self.win.addch(ch)
            except curses.error:
                pass
            if not self.insert_mode or not curses.ascii.isprint(oldch):
                break
            ch = oldch
            _, x = self.win.getyx()
            # Remember where to put the cursor back since we are in insert_mode.
            if backx is None:
                backx = x

        if backx is not None:
            self.win.move(0, backx)

    def do_command(self, ch):
        """Process a single editing command."""
        logging.debug(f"textpad.do_command {ch}")
        self._update_maxx()
        _, x = self.win.getyx()
        if curses.ascii.isprint(ch):
            if x < self.maxx:
                self._insert_printable_char(ch)
        elif ch == curses.ascii.NL:
            return 0
        elif ch == curses.ascii.SOH:                      # ^a
            self.win.move(0, 0)
        elif ch in (
            curses.ascii.STX,
            curses.KEY_LEFT,
            curses.ascii.BS,
            curses.KEY_BACKSPACE
        ):
            if x > 0:
                self.win.move(0, x - 1)
            if ch in (curses.ascii.BS, curses.KEY_BACKSPACE):
                self.win.delch()
        elif ch == curses.ascii.EOT:                      # ^d
            self.win.delch()
        elif ch == curses.ascii.ENQ:                      # ^e
            if self.stripspaces:
                self.win.move(0, self._end_of_line())
            else:
                self.win.move(0, self.maxx)
        elif ch in (curses.ascii.ACK, curses.KEY_RIGHT):  # ^f
            if x < self.maxx:
                self.win.move(0, x + 1)
        elif ch == curses.ascii.VT:                       # ^k
            if x == 0 and self._end_of_line() == 0:
                self.win.deleteln()
            else:
                # First undo the effect of self._end_of_line.
                self.win.move(0, x)
                self.win.clrtoeol()
        elif ch == curses.ascii.FF:                       # ^l
            self.win.refresh()
        return 1

    def gather(self):
        """Collect and return the contents of the window."""
        result = ""
        self._update_maxx()
        self.win.move(0, 0)
        stop = self._end_of_line()
        for x in range(self.maxx + 1):
            if self.stripspaces and x > stop:
                break
            result = result + chr(curses.ascii.ascii(self.win.inch(0, x)))
        return result

    def edit(self, validate=None):
        """Edit in the widget window and collect the results."""
        while True:
            ch = self.win.getch()
            if validate:
                ch = validate(ch)
            if not ch:
                continue
            if not self.do_command(ch):
                break
            self.win.refresh()
        return self.gather()
