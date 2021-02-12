import curses
import curses.ascii
import curses.textpad
import os

from bebop.colors import ColorPair, init_colors
from bebop.gemtext import parse_gemtext
from bebop.mouse import ButtonState
from bebop.navigation import join_url, parse_url
from bebop.protocol import Request, Response
from bebop.rendering import format_elements, render_lines


class Screen:
    
    MAX_COLS = 1000

    def __init__(self, cert_stash):
        self.stash = cert_stash
        self.screen = None
        self.dim = (0, 0)
        self.content_pad = None
        self.content_pad_dim = (0, 0)
        self.status_window = None
        self.command_window = None
        self.command_textbox = None
        self.metalines = []
        self.current_url = ""
        self.current_line = 0
        self.current_column = 0
        self.links = {}
        self.status_data = ("", 0)

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
        init_colors()
        curses.mousemask(curses.ALL_MOUSE_EVENTS)

        self.dim = self.screen.getmaxyx()
        self.content_pad_dim = (self.h - 2, Screen.MAX_COLS)
        self.content_pad = curses.newpad(*self.content_pad_dim)
        self.content_pad.scrollok(True)
        self.content_pad.idlok(True)
        self.status_window = self.screen.subwin(
            *self.line_dim,
            *self.status_window_pos,
        )
        self.command_window = self.screen.subwin(
            *self.line_dim,
            *self.command_window_pos,
        )
        curses.curs_set(0)

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
                self.set_status(f"h {self.h} w {self.w} cl {self.current_line} cc {self.current_column}")
            elif char == ord("r"):
                self.refresh_content()
            elif char == ord("h"):
                if self.current_column > 0:
                    self.current_column -= 1
                    self.refresh_content()
            elif char == ord("j"):
                self.scroll_content(1)
            elif char == ord("k"):
                self.scroll_content(1, scroll_up=True)
            elif char == ord("l"):
                if self.current_column < Screen.MAX_COLS - self.w:
                    self.current_column += 1
                    self.refresh_content()
            elif curses.ascii.isdigit(char):
                self.handle_digit_input(char)
            elif char == curses.KEY_MOUSE:
                self.handle_mouse(*curses.getmouse())
            elif char == curses.KEY_RESIZE:
                self.handle_resize()

    @property
    def content_window_refresh_size(self):
        return self.h - 3, self.w - 1

    @property
    def status_window_pos(self):
        return self.h - 2, 0

    @property
    def command_window_pos(self):
        return self.h - 1, 0

    @property
    def line_dim(self):
        return 1, self.w

    def refresh_windows(self):
        self.refresh_content()
        self.refresh_status()
        self.clear_command()

    def refresh_content(self):
        """Refresh content pad's view using the current line/column."""
        refresh_size = self.content_window_refresh_size
        if refresh_size[0] <= 0 or refresh_size[1] <= 0:
            return
        self.content_pad.refresh(
            self.current_line, self.current_column, 0, 0, *refresh_size
        )

    def refresh_status(self):
        """Refresh status line contents."""
        text, pair = self.status_data
        text = text[:self.w - 1]
        self.status_window.addstr(0, 0, text, curses.color_pair(pair))
        self.status_window.clrtoeol()
        self.status_window.refresh()

    def scroll_content(self, num_lines: int, scroll_up: bool =False):
        """Make the content pad scroll up and down by *num_lines*."""
        if scroll_up:
            min_line = 0
            if self.current_line > min_line:
                self.current_line = max(self.current_line - num_lines, min_line)
                self.refresh_content()
        else:
            max_line = self.content_pad_dim[0] - self.h + 2
            if self.current_line < max_line:
                self.current_line = min(self.current_line + num_lines, max_line)
                self.refresh_content()

    def set_status(self, text):
        """Set a regular message in the status bar."""
        self.status_data = text, ColorPair.NORMAL
        self.refresh_status()

    def set_status_error(self, text):
        """Set an error message in the status bar."""
        self.status_data = f"Error: {text}", ColorPair.ERROR
        self.refresh_status()

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

        if response.code != 20:
            self.set_status_error(f"unknown response code {response.code}.")
            return

        self.set_status(url)
        self.current_url = url
        self.show_gemtext(response.content)

    def show_gemtext(self, gemtext: bytes):
        """Render Gemtext data in the content pad."""
        elements = parse_gemtext(gemtext)
        self.metalines = format_elements(elements, 80)
        self.links = {
            meta["link_id"]: meta["url"]
            for meta, _ in self.metalines
            if "link_id" in meta and "url" in meta
        }

        self.content_pad.clear()
        h, w = render_lines(self.metalines, self.content_pad, Screen.MAX_COLS)
        self.content_pad_dim = (h, w)
        self.current_line = 0
        self.current_column = 0
        self.refresh_content()

    def focus_command(self, command_char, validator=None, prefix=""):
        """Give user focus to the command bar.

        Show the command char and give focus to the command textbox. The
        validator function is passed to the textbox.

        Arguments:
        - command_char: char to display before the command line.
        - validator: function to use to validate the input chars.
        - prefix: string to insert before the cursor in the command line.

        Returns:
        User input as string. The string will be empty if the validator raised
        an EscapeInterrupt.
        """
        assert self.command_window is not None
        self.command_window.clear()
        self.command_window.refresh()
        self.command_textbox = curses.textpad.Textbox(self.command_window)
        self.command_window.addstr(command_char + prefix)
        curses.curs_set(1)
        try:
            command = self.command_textbox.edit(validator)[1:]
        except EscapeCommandInterrupt:
            command = ""
        except TerminateCommandInterrupt as exc:
            command = exc.command
        curses.curs_set(0)
        self.clear_command()
        return command

    def gather_current_command(self):
        """Return the string currently written by the user in command line."""
        return self.command_textbox.gather()[1:].rstrip()

    def clear_command(self):
        """Clear the command line """
        self.command_window.clear()
        self.command_window.refresh()
        self.screen.delch(self.h - 1, 0)
        self.screen.refresh()

    def input_common_command(self):
        """Focus command line to type a regular command. Currently useless."""
        return self.focus_command(":", self.validate_common_char)

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
            text = self.gather_current_command()
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

        Examples
        - I have 3 links. Pressing "2" takes me to link 2.
        - I have 15 links. Pressing "3" and Enter takes me to link 2.
        - I have 15 links. Pressing "1" and "2" takes me to link 12 (no
          ambiguity, so Enter is not required).
        - I have 456 links. Pressing "1", "2" and Enter takes me to link 12.
        - I have 456 links. Pressing "1", "2" and "6" takes me to link 126 (no
          ambiguity as well).
        """
        digit = init_char & 0xf
        num_links = len(self.links)
        if num_links < 10:
            self.open_link(digit)
            return
        required_digits = 0
        while num_links:
            required_digits += 1
            num_links //= 10
        link_input = self.focus_command(
            "~",
            validator=lambda ch: self._validate_link_digit(ch, required_digits),
            prefix=chr(init_char),
        )
        try:
            link_id = int(link_input)
        except ValueError:
            self.set_status_error("invalid link ID")
            return
        self.open_link(link_id)

    def _validate_link_digit(self, ch: int, required_digits: int):
        """Handle input chars to be used as link ID."""
        # Handle common chars.
        ch = self.validate_common_char(ch)
        # Only accept digits. If we reach the amount of required digits, open
        # link now and leave command line. Else just process it.
        if curses.ascii.isdigit(ch):
            digits = self.gather_current_command()
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


    def open_link(self, link_id: int):
        """Open the link with this link ID."""
        if not link_id in self.links:
            self.set_status_error(f"unknown link ID {link_id}.")
            return
        self.open_url(self.links[link_id])

    def handle_mouse(self, mouse_id: int, x: int, y: int, z: int, bstate: int):
        """Handle mouse events.

        Right now, only vertical scrolling is handled.
        """
        if bstate & ButtonState.SCROLL_UP:
            self.scroll_content(3, scroll_up=True)
        elif bstate & ButtonState.SCROLL_DOWN:
            self.scroll_content(3)

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
        self.status_window.resize(*self.line_dim)
        self.command_window.resize(*self.line_dim)
        # Move the windows to their new position if that's still possible.
        if self.status_window_pos[0] >= 0:
            self.status_window.mvwin(*self.status_window_pos)
        if self.command_window_pos[0] >= 0:
            self.command_window.mvwin(*self.command_window_pos)
        # If the content pad does not fit its whole place, we have to clean the
        # gap between it and the status line. Refresh all screen.
        if self.content_pad_dim[0] < self.h - 2:
            self.screen.clear()
            self.screen.refresh()
        self.refresh_windows()


class EscapeCommandInterrupt(Exception):
    """Signal that ESC has been pressed during command line."""
    pass


class TerminateCommandInterrupt(Exception):
    """Signal that validation ended command line input early. Use `command`."""

    def __init__(self, command: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command
