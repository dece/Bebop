import curses
import curses.ascii
import curses.textpad
import os

from bebop.colors import ColorPair, init_colors
from bebop.command_line import (CommandLine, EscapeCommandInterrupt,
    TerminateCommandInterrupt)
from bebop.mouse import ButtonState
from bebop.navigation import join_url, parse_url
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
                if self.page.scroll_left():
                    self.refresh_page()
            elif char == ord("j"):
                if self.page.scroll_v(1, self.h - 2):
                    self.refresh_page()
            elif char == ord("k"):
                if self.page.scroll_v(-1, self.h - 2):
                    self.refresh_page()
            elif char == ord("l"):
                if self.page.scroll_right(self.w):
                    self.refresh_page()
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

    def open_url(self, url):
        """Try to open an URL.

        If the URL is not strictly absolute, it will be opened relatively to the
        current URL, unless there is no current URL yet.
        """
        if self.current_url:
            parts = parse_url(url)
        else:
            parts = parse_url(url, absolute=True)
        if parts.scheme == "gemini":
            if not parts.netloc:
                url = join_url(self.current_url, url)
            self.open_gemini_url(url)
        else:
            self.set_status_error(f"protocol {parts.scheme} not supported.")

    def open_gemini_url(self, url):
        """Open a Gemini URL and set the formatted response as content."""
        self.set_status(f"Loading {url}")
        req = Request(url, self.stash)
        connected = req.connect()
        if not connected:
            if req.state == Request.STATE_ERROR_CERT:
                self.set_status_error("certificate was missing or corrupt.")
            elif req.state == Request.STATE_UNTRUSTED_CERT:
                self.set_status_error("certificate has been changed.")
                # TODO propose the user ways to handle this.
            else:
                self.set_status_error("connection failed.")
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
            self.set_status_error("server response parsing failed.")
            return

        if response.code == 20:
            self.load_page(response.content)
            self.current_url = url
            self.set_status(url)
        elif response.generic_code == 30 and response.meta:
            self.open_gemini_url(response.meta)

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
        - If the highest link ID on the page is less than 10, pressing the key
          takes you to the link.
        - If it's higher than 10, the user either inputs as many digits required
          to disambiguate the link ID, or press enter to validate her input.

        Examples:
        - I have 3 links. Pressing "2" takes me to link 2.
        - I have 15 links. Pressing "3" and Enter takes me to link 2.
        - I have 15 links. Pressing "1" and "2" takes me to link 12 (no
          ambiguity, so Enter is not required).
        - I have 456 links. Pressing "1", "2" and Enter takes me to link 12.
        - I have 456 links. Pressing "1", "2" and "6" takes me to link 126 (no
          ambiguity as well).
        """
        digit = init_char & 0xf
        links = self.page.links
        num_links = len(links)
        if num_links < 10:
            self.open_link(links, digit)
            return
        required_digits = 0
        while num_links:
            required_digits += 1
            num_links //= 10
        validator = lambda ch: self._validate_link_digit(ch, required_digits)
        link_input = self.command_line.focus("&", validator, chr(init_char))
        try:
            link_id = int(link_input)
        except ValueError:
            self.set_status_error("invalid link ID")
            return
        self.open_link(links, link_id)

    def _validate_link_digit(self, ch: int, required_digits: int):
        """Handle input chars to be used as link ID."""
        # Handle common chars.
        ch = self.validate_common_char(ch)
        # Only accept digits. If we reach the amount of required digits, open
        # link now and leave command line. Else just process it.
        if curses.ascii.isdigit(ch):
            digits = self.command_line.gather()
            if len(digits) + 1 == required_digits:
                raise TerminateCommandInterrupt(digits + chr(ch))
            return ch
        # If not a digit but a printable character, ignore it.
        if curses.ascii.isprint(ch):
            return 0
        # Everything else could be a control character and should be processed.
        return ch

    def disambiguate_link_id(self, digits: str, max_digits: int):
        if len(digits) == max_digits:
            return digits

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
            self.page.scroll_v(-3)
        elif bstate & ButtonState.SCROLL_DOWN:
            self.page.scroll_v(3, self.h - 2)

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
