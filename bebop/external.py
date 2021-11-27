"""Call external commands."""

import curses
import logging
import re
import subprocess
import tempfile

from bebop.page import Page


def _pre_exec():
    curses.nocbreak()
    curses.echo()
    curses.curs_set(1)


def _post_exec():
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()


def open_external_program(command):
    """Call command as a subprocess, suspending curses rendering.

    The caller has to refresh whatever windows it manages after calling this
    method or garbage may be left on the screen.

    Returns:
    True if no exception occured.
    """
    _pre_exec()
    result = True
    try:
        subprocess.run(command)
    except OSError as exc:
        logging.error(f"Failed to run '{command}': {exc}")
        result = False
    _post_exec()
    return result


SUB_URL_RE = re.compile(r"(?<!\$)\$u")
SUB_SRC_RE = re.compile(r"(?<!\$)\$s")
SUB_LINK_RE = re.compile(r"(?<!\$)\$(\d+)")
SUB_LITERAL_RE = re.compile(r"\$\$")


def substitute_external_command(command: str, url: str, page: Page):
    """Substitute "$" parts of the command with corresponding values.

    Valid substitutions are:
    - $u = current url
    - $n (with n any positive number) = link url
    - $s = current page source temp file
    - $$ = $

    Returns:
    The command with all the template parts replaced with the corresponding
    strings.

    Raises:
    ValueError if a substitution is wrong, e.g. a link ID which does not exist.
    """
    # URL substitution.
    command = SUB_URL_RE.sub(url, command)
    # Source file substitution.
    if SUB_SRC_RE.search(command):
        with tempfile.NamedTemporaryFile("wt", delete=False) as source_file:
            source_file.write(page.source)
            command = SUB_SRC_RE.sub(source_file.name, command)
    # Link ID substitution.
    command = SUB_LINK_RE.sub(lambda m: page.links[int(m.group(1))], command)
    # Literal dollar sign.
    command = SUB_LITERAL_RE.sub("$", command)
    return command
