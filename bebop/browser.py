import curses
import curses.ascii
import curses.textpad
import os
from math import inf
from webbrowser import open_new_tab

from bebop.colors import ColorPair, init_colors
from bebop.command_line import (CommandLine, EscapeCommandInterrupt,
    TerminateCommandInterrupt)
from bebop.history import History
from bebop.mouse import ButtonState
from bebop.navigation import join_url, parse_url, sanitize_url, set_parameter
from bebop.page import Page
from bebop.protocol import Request, Response


class Browser:
    """Manage the events, inputs and rendering."""
    
    def __init__(self, cert_stash):
        self.stash = cert_stash
        self.screen = None
        self.dim = (0, 0)
        self.tab = None
        self.status_line = None
        self.command_line = None
        self.status_data = ("", 0)
        self.current_url = ""
        self.running = True
        self.history = History()

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
        while self.running:
            if pending_url:
                self.open_url(pending_url)
                pending_url = None

            char = self.screen.getch()
            if char == ord(":"):
                self.quick_command("")
            elif char == ord("r"):
                self.reload_page()
            elif char == ord("s"):
                self.set_status(f"h {self.h} w {self.w}")
            elif char == ord("h"):
                self.scroll_page_horizontally(-1)
            elif char == ord("H"):
                self.scroll_page_horizontally(-3)
            elif char == ord("j"):
                self.scroll_page_vertically(1)
            elif char == ord("J"):
                self.scroll_page_vertically(3)
            elif char == ord("k"):
                self.scroll_page_vertically(-1)
            elif char == ord("K"):
                self.scroll_page_vertically(-3)
            elif char == ord("l"):
                self.scroll_page_horizontally(1)
            elif char == ord("L"):
                self.scroll_page_horizontally(3)
            elif char == ord("f"):
                self.scroll_page_vertically(self.page_pad_size[0])
            elif char == ord("b"):
                self.scroll_page_vertically(-self.page_pad_size[0])
            elif char == ord("o"):
                self.quick_command("open")
            elif char == ord("p"):
                self.go_back()
            elif char == ord("g"):
                char = self.screen.getch()
                if char == ord("g"):
                    self.scroll_page_vertically(-inf)
            elif char == ord("G"):
                self.scroll_page_vertically(inf)
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
        """Refresh all windows and clear command line."""
        self.refresh_page()
        self.refresh_status_line()
        self.command_line.clear()

    def refresh_page(self):
        """Refresh the current page pad; it does not reload the page."""
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
        self.status_data = text, ColorPair.ERROR
        self.refresh_status_line()

    def open_url(self, url, base_url=None, redirects=0, assume_absolute=False):
        """Try to open an URL.

        This function assumes that the URL can be from an user and thus tries a
        few things to make it work.

        If there is no current URL (e.g. we just started) or `assume_absolute`
        is True, assume it is an absolute URL. In other cases, parse it normally
        and later check if it has to be used relatively to the current URL.
        
        Arguments:
        - url: an URL string, may not be completely compliant.
        - base_url: an URL string to use as base in case `url` is relative.
        - redirections: number of redirections we did yet for the same request.
        - assume_absolute: assume we intended to use an absolute URL if True.
        """
        if redirects > 5:
            self.set_status_error(f"Too many redirections ({url}).")
            return
        if assume_absolute or not self.current_url:
            parts = parse_url(url, absolute=True)
            join = False
        else:
            parts = parse_url(url)
            join = True
        if parts.scheme == "gemini":
            # If there is no netloc, this is a relative URL.
            if join or base_url:
                url = join_url(base_url or self.current_url, url)
            self.open_gemini_url(sanitize_url(url), redirects)
        elif parts.scheme.startswith("http"):
            self.open_web_url(url)
        else:
            self.set_status_error(f"Protocol {parts.scheme} not supported.")

    def open_gemini_url(self, url, redirects=0, history=True):
        """Open a Gemini URL and set the formatted response as content."""
        self.set_status(f"Loading {url}")
        req = Request(url, self.stash)
        connected = req.connect()
        if not connected:
            if req.state == Request.STATE_ERROR_CERT:
                error = f"Certificate was missing or corrupt ({url})."
                self.set_status_error(error)
            elif req.state == Request.STATE_UNTRUSTED_CERT:
                self.set_status_error(f"Certificate has been changed ({url}).")
                # TODO propose the user ways to handle this.
            elif req.state == Request.STATE_CONNECTION_FAILED:
                error = f": {req.error}" if req.error else "."
                self.set_status_error(f"Connection failed ({url}){error}")
            else:
                self.set_status_error(f"Connection failed ({url}).")
            return

        if req.state == Request.STATE_INVALID_CERT:
            # TODO propose abort / temp trust
            pass
        elif req.state == Request.STATE_UNKNOWN_CERT:
            # TODO propose abort / temp trust / perm trust
            pass
        else:
            pass # TODO

        data = req.proceed()
        if not data:
            self.set_status_error(f"Server did not respond in time ({url}).")
            return
        response = Response.parse(data)
        if not response:
            self.set_status_error(f"Server response parsing failed ({url}).")
            return

        if response.code == 20:
            self.load_page(response.content)
            if self.current_url and history:
                self.history.push(self.current_url)
            self.current_url = url
            self.set_status(url)
        elif response.generic_code == 30 and response.meta:
            self.open_url(response.meta, base_url=url, redirects=redirects + 1)
        elif response.generic_code in (40, 50):
            error = f"Server error: {response.meta or Response.code.name}"
            self.set_status_error(error)
        elif response.generic_code == 10:
            self.handle_input_request(url, response)

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

    def take_user_input(self, type_char: str =":", prefix: str =""):
        """Focus command line to let the user type something."""
        return self.command_line.focus(
            type_char,
            validator=self.validate_common_char,
            prefix=prefix,
        )

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

    def quick_command(self, command):
        """Shortcut method to take user input with a prefixed command string."""
        prefix = f"{command} " if command else ""
        user_input = self.take_user_input(prefix=prefix)
        if not user_input:
            return
        self.process_command(user_input)

    def process_command(self, command_text: str):
        words = command_text.split()
        command = words[0]
        if command in ("o", "open"):
            self.open_url(words[1], assume_absolute=True)
        elif command in ("q", "quit"):
            self.running = False

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
        if not link_input:
            return
        try:
            link_id = int(link_input)
        except ValueError as exc:
            self.set_status_error(f"Invalid link ID {link_input}.")
            return
        self.open_link(links, link_id)

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
            self.set_status_error(f"Unknown link ID {link_id}.")
            return
        self.open_url(links[link_id])

    def handle_input_request(self, from_url: str, response: Response):
        if response.meta:
            self.set_status(f"Input needed: {response.meta}")
        else:
            self.set_status("Input needed:")
        user_input = self.take_user_input("?")
        if user_input:
            url = set_parameter(from_url, user_input)
            self.open_gemini_url(url)

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

    def scroll_page_vertically(self, by_lines):
        window_height = self.h - 2
        require_refresh = False
        if by_lines == inf:
            require_refresh = self.page.go_to_end(window_height)
        elif by_lines == -inf:
            require_refresh = self.page.go_to_beginning()
        else:
            require_refresh = self.page.scroll_v(by_lines, window_height)
        if require_refresh:
            self.refresh_page()

    def scroll_page_horizontally(self, by_columns):
        if self.page.scroll_h(by_columns, self.w):
            self.refresh_page()

    def reload_page(self):
        if self.current_url:
            self.open_gemini_url(self.current_url, history=False)

    def go_back(self):
        """Go back in history if possible."""
        if self.history.has_links():
            self.open_gemini_url(self.history.pop(), history=False)

    def open_web_url(self, url):
        """Open a Web URL. Currently relies in Python's webbrowser module."""
        self.set_status(f"Opening {url}")
        open_new_tab(url)
