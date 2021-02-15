import curses
import curses.ascii
import curses.textpad
import os

from bebop.colors import ColorPair, init_colors
from bebop.command_line import (CommandLine, EscapeCommandInterrupt,
    TerminateCommandInterrupt)
from bebop.mouse import ButtonState
from bebop.navigation import join_url, parse_url, sanitize_url
from bebop.page import Page
from bebop.protocol import Request, Response


class Screen:
    
    def __init__(self, cert_stash):
        self.stash = cert_stash
        self.screen = None
        self.dim = (0, 0)
        self.tab = None
        self.status_line = None
        self.command_line = None
        self.status_data = ("", 0)
        self.current_url = ""
        self.history = []

    @property
    def h(self):
        return self.dim[0]

    @property
    def w(self):
        return self.dim[1]

    def run(self, *args, **kwargs):
        """Use curses' wrapper around _run."""
        os.environ.setdefault("ESCDELAY", "25")
        curses.wrapper(self._run, *args, **kwargs)

    def _run(self, stdscr, start_url=None):
        """Start displaying content and handling events."""
        self.screen = stdscr
        self.screen.clear()
        self.screen.refresh()

        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        curses.curs_set(0)
        init_colors()

        self.dim = self.screen.getmaxyx()
        self.page = Page(self.h - 2)
        self.status_line = self.screen.subwin(
            *self.line_dim,
            *self.status_line_pos,
        )
        command_line_window = self.screen.subwin(
            *self.line_dim,
            *self.command_line_pos,
        )
        self.command_line = CommandLine(command_line_window)

        pending_url = start_url
        running = True
        while running:
            if pending_url:
                self.open_gemini_url(pending_url)
                pending_url = None

            char = self.screen.getch()
            if char == ord("q"):
                running = False
            elif char == ord(":"):
                command = self.input_common_command()
                self.set_status(f"Command: {command}")
            elif char == ord("s"):
                self.set_status(f"h {self.h} w {self.w}")
            elif char == ord("h"):
                self.scroll_page_horizontally(-1)
            elif char == ord("j"):
                self.scroll_page_vertically(1)
            elif char == ord("k"):
                self.scroll_page_vertically(-1)
            elif char == ord("l"):
                self.scroll_page_horizontally(1)
            elif char == ord("f"):
                self.scroll_page_vertically(self.page_pad_size[0])
            elif char == ord("b"):
                self.scroll_page_vertically(-self.page_pad_size[0])
            elif char == ord("H"):
                self.go_back()
            elif curses.ascii.isdigit(char):
                self.handle_digit_input(char)
            elif char == curses.KEY_MOUSE:
                self.handle_mouse(*curses.getmouse())
            elif char == curses.KEY_RESIZE:
                self.handle_resize()

    @property
    def page_pad_size(self):
        return self.h - 3, self.w - 1

    @property
    def status_line_pos(self):
        return self.h - 2, 0

    @property
    def command_line_pos(self):
        return self.h - 1, 0

    @property
    def line_dim(self):
        return 1, self.w

    def refresh_windows(self):
        self.refresh_page()
        self.refresh_status_line()
        self.command_line.clear()

    def refresh_page(self):
        self.page.refresh_content(*self.page_pad_size)

    def refresh_status_line(self):
        """Refresh status line contents."""
        text, pair = self.status_data
        text = text[:self.w - 1]
        self.status_line.addstr(0, 0, text, curses.color_pair(pair))
        self.status_line.clrtoeol()
        self.status_line.refresh()

    def set_status(self, text):
        """Set a regular message in the status bar."""
        self.status_data = text, ColorPair.NORMAL
        self.refresh_status_line()

    def set_status_error(self, text):
        """Set an error message in the status bar."""
        self.status_data = f"Error: {text}", ColorPair.ERROR
        self.refresh_status_line()

    def open_url(self, url, redirections=0):
        """Try to open an URL.

        If the URL is not strictly absolute, it will be opened relatively to the
        current URL, unless there is no current URL yet.
        """
        if redirections > 5:
            self.set_status_error(f"too many redirections ({url})")
            return
        if self.current_url:
            parts = parse_url(url)
        else:
            parts = parse_url(url, absolute=True)
        if parts.scheme == "gemini":
            # If there is no netloc, this is a relative URL.
            if not parts.netloc:
                url = join_url(self.current_url, url)
            self.open_gemini_url(sanitize_url(url), redirections)
        else:
            self.set_status_error(f"protocol {parts.scheme} not supported")

    def open_gemini_url(self, url, redirections=0):
        """Open a Gemini URL and set the formatted response as content."""
        with open("/tmp/a", "at") as f: f.write(url + "\n")
        self.set_status(f"Loading {url}")
        req = Request(url, self.stash)
        connected = req.connect()
        if not connected:
            if req.state == Request.STATE_ERROR_CERT:
                error = f"certificate was missing or corrupt ({url})"
                self.set_status_error(error)
            elif req.state == Request.STATE_UNTRUSTED_CERT:
                self.set_status_error(f"certificate has been changed ({url})")
                # TODO propose the user ways to handle this.
            else:
                self.set_status_error(f"connection failed ({url})")
            return

        if req.state == Request.STATE_INVALID_CERT:
            # TODO propose abort / temp trust
            pass
        elif req.state == Request.STATE_UNKNOWN_CERT:
            # TODO propose abort / temp trust / perm trust
            pass
        else:
            pass # TODO

        response = Response.parse(req.proceed())
        if not response:
            self.set_status_error(f"server response parsing failed ({url})")
            return

        if response.code == 20:
            self.load_page(response.content)
            if self.current_url:
                self.history.append(self.current_url)
            self.current_url = url
            self.set_status(url)
        elif response.generic_code == 30 and response.meta:
            self.open_url(response.meta, redirections=redirections + 1)
        elif response.generic_code in (40, 50):
            self.set_status_error(response.meta or Response.code.name)

    def load_page(self, gemtext: bytes):
        """Load Gemtext data as the current page."""
        old_pad_height = self.page.dim[0]
        self.page.show_gemtext(gemtext)
        if self.page.dim[0] < old_pad_height:
            self.screen.clear()
            self.screen.refresh()
            self.refresh_windows()
        else:
            self.refresh_page()

    def input_common_command(self):
        """Focus command line to type a regular command. Currently useless."""
        return self.command_line.focus(":", self.validate_common_char)

    def validate_common_char(self, ch: int):
        """Generic input validator, handles a few more cases than default.

        This validator can be used as a default validator as it handles, on top
        of the Textbox defaults:
        - Erasing the first command char, i.e. clearing the line, cancels the
          command input.
        - Pressing ESC also cancels the input.

        This validator can be safely called at the beginning of other validators
        to handle the keys above.
        """
        if ch == curses.KEY_BACKSPACE:  # Cancel input if all line is cleaned.
            text = self.command_line.gather()
            if len(text) == 0:
                raise EscapeCommandInterrupt()
        elif ch == curses.ascii.ESC:  # Could be ESC or ALT
            self.screen.nodelay(True)
            ch = self.screen.getch()
            if ch == -1:
                raise EscapeCommandInterrupt()
            self.screen.nodelay(False)
        return ch

    def handle_digit_input(self, init_char: int):
        """Handle a initial digit input by the user.

        When a digit key is pressed, the user intents to visit a link (or
        dropped something on the numpad). To reduce the number of key types
        needed, Bebop uses the following algorithm:
        - If the current user input identifies a link without ambiguity, it is
          used directly.
        - If it is ambiguous, the user either inputs as many digits required
          to disambiguate the link ID, or press enter to validate her input.

        Examples:
        - I have 3 links. Pressing "2" takes me to link 2.
        - I have 15 links. Pressing "3" takes me to link 3 (no ambiguity).
        - I have 15 links. Pressing "1" and "2" takes me to link 12.
        - I have 456 links. Pressing "1", "2" and Enter takes me to link 12.
        - I have 456 links. Pressing "1", "2" and "6" takes me to link 126.
        """
        digit = init_char & 0xf
        links = self.page.links
        num_links = len(links)
        # If there are less than 10 links, just open it now.
        if num_links < 10:
            self.open_link(links, digit)
            return
        # Else check if the digit alone is sufficient.
        digit = chr(init_char)
        max_digits = 0
        while num_links:
            max_digits += 1
            num_links //= 10
        disambiguous = self.disambiguate_link_id(digit, links, max_digits)
        if disambiguous is not None:
            self.open_link(links, disambiguous)
            return
        # Else, focus the command line to let the user input more digits.
        validator = lambda ch: self._validate_link_digit(ch, links, max_digits)
        link_input = self.command_line.focus("&", validator, digit)
        try:
            self.open_link(links, int(link_input))
        except ValueError:
            self.set_status_error("invalid link ID")

    def _validate_link_digit(self, ch: int, links, max_digits: int):
        """Handle input chars to be used as link ID."""
        # Handle common chars.
        ch = self.validate_common_char(ch)
        # Only accept digits. If we reach the amount of required digits, open
        # link now and leave command line. Else just process it.
        if curses.ascii.isdigit(ch):
            digits = self.command_line.gather() + chr(ch)
            disambiguous = self.disambiguate_link_id(digits, links, max_digits)
            if disambiguous is not None:
                raise TerminateCommandInterrupt(disambiguous)
            return ch
        # If not a digit but a printable character, ignore it.
        if curses.ascii.isprint(ch):
            return 0
        # Everything else could be a control character and should be processed.
        return ch

    def disambiguate_link_id(self, digits: str, links, max_digits: int):
        """Return the only possible link ID as str, or None on ambiguities."""
        if len(digits) == max_digits:
            return int(digits)
        candidates = [
            link_id for link_id, url in links.items()
            if str(link_id).startswith(digits)
        ]
        return candidates[0] if len(candidates) == 1 else None

    def open_link(self, links, link_id: int):
        """Open the link with this link ID."""
        if not link_id in links:
            self.set_status_error(f"unknown link ID {link_id}.")
            return
        self.open_url(links[link_id])

    def handle_mouse(self, mouse_id: int, x: int, y: int, z: int, bstate: int):
        """Handle mouse events.

        Right now, only vertical scrolling is handled.
        """
        if bstate & ButtonState.SCROLL_UP:
            self.scroll_page_vertically(-3)
        elif bstate & ButtonState.SCROLL_DOWN:
            self.scroll_page_vertically(3)

    def handle_resize(self):
        """Try to not make everything collapse on resizes."""
        # Refresh the whole screen before changing windows to avoid random
        # blank screens.
        self.screen.refresh()
        old_dim = self.dim
        self.dim = self.screen.getmaxyx()
        # Avoid work if the resizing does not impact us.
        if self.dim == old_dim:
            return
        # Resize windows to fit the new dimensions. Content pad will be updated
        # on its own at the end of the function.
        self.status_line.resize(*self.line_dim)
        self.command_line.window.resize(*self.line_dim)
        # Move the windows to their new position if that's still possible.
        if self.status_line_pos[0] >= 0:
            self.status_line.mvwin(*self.status_line_pos)
        if self.command_line_pos[0] >= 0:
            self.command_line.window.mvwin(*self.command_line_pos)
        # If the content pad does not fit its whole place, we have to clean the
        # gap between it and the status line. Refresh all screen.
        if self.page.dim[0] < self.h - 2:
            self.screen.clear()
            self.screen.refresh()
        self.refresh_windows()

    def scroll_page_vertically(self, by_lines: int):
        if self.page.scroll_v(by_lines, self.h - 2):
            self.refresh_page()

    def scroll_page_horizontally(self, by_columns: int):
        if self.page.scroll_h(by_columns, self.w):
            self.refresh_page()

    def go_back(self):
        """Go back in history if possible."""
        if self.history:
            self.open_gemini_url(self.history.pop())
