"""Call external commands."""

import curses
import subprocess


def open_external_program(command):
    """Call command as a subprocess, suspending curses rendering.

    The caller has to refresh whatever windows it manages after calling this
    method or garbage may be left on the screen.
    """
    curses.nocbreak()
    curses.echo()
    curses.curs_set(1)
    subprocess.run(command)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
