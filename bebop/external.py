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
    subprocess.run(command)
    curses.noecho()
    curses.cbreak()
