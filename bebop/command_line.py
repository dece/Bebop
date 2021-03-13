"""Integrated command-line implementation."""

import curses
import curses.ascii
import curses.textpad
import typing

from bebop.links import Links


class CommandLine:
    """Basic and flaky command-line à la Vim, using curses module's Textbox."""

    def __init__(self, window):
        self.window = window
        self.textbox = None

    def clear(self):
        """Clear command-line contents."""
        self.window.clear()
        self.window.refresh()

    def focus(self, command_char, validator=None, prefix=""):
        """Give user focus to the command bar.

        Show the command char and give focus to the command textbox. The
        validator function is passed to the textbox.

        Arguments:
        - command_char: char to display before the command line; it must be an
          str of length 1, else the return value of `gather` might be wrong.
        - validator: function to use to validate the input chars; if omitted,
          `validate_common_input` is used.
        - prefix: string to insert before the cursor in the command line.

        Returns:
        User input as string. The string will be empty if the validator raised
        an EscapeInterrupt.
        """
        self.window.clear()
        self.window.refresh()
        self.textbox = curses.textpad.Textbox(self.window)
        self.window.addstr(command_char + prefix)
        curses.curs_set(1)
        try:
            command = self.textbox.edit(validator or self.validate_common_input)
        except EscapeCommandInterrupt:
            command = ""
        except TerminateCommandInterrupt as exc:
            command = exc.command
        command = command[1:].rstrip()
        curses.curs_set(0)
        self.clear()
        return command

    def gather(self):
        """Return the string currently written by the user in command line."""
        return self.textbox.gather()[1:].rstrip()

    def validate_common_input(self, ch: int):
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
            text = self.gather()
            if len(text) == 0:
                raise EscapeCommandInterrupt()
        elif ch == curses.ascii.ESC:  # Could be ESC or ALT
            self.window.nodelay(True)
            ch = self.window.getch()
            if ch == -1:
                raise EscapeCommandInterrupt()
            self.window.nodelay(False)
        return ch

    def focus_for_link_navigation(self, init_char: int, links: Links):
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

        Arguments:
        - init_char: the first char (code) being pressed.
        - links: accessible Links.

        Returns:
        The tuple (error, value); if error is 0, value is the link ID to use; if
        error is 1, discard value and do nothing; if error is 2, value is an
        error than can be showed to the user.
        """
        digit = init_char & 0xf
        num_links = len(links)
        # If there are less than 10 links, just open it now.
        if num_links < 10:
            return 0, digit
        # Else check if the digit alone is sufficient.
        digit = chr(init_char)
        max_digits = 0
        while num_links:
            max_digits += 1
            num_links //= 10
        candidates = links.disambiguate(digit, max_digits)
        if len(candidates) == 1:
            return 0, candidates[0]
        # Else, focus the command line to let the user input more digits.
        validator = lambda ch: self.validate_link_digit(ch, links, max_digits)
        link_input = self.focus("&", validator, digit)
        if not link_input:
            return 1, None
        try:
            link_id = int(link_input)
        except ValueError as exc:
            return 2, f"Invalid link ID {link_input}."
        return 0, link_id

    def validate_link_digit(self, ch: int, links: Links, max_digits: int):
        """Handle input chars to be used as link ID."""
        # Handle common chars.
        ch = self.validate_common_input(ch)
        # Only accept digits. If we reach the amount of required digits, open
        # link now and leave command line. Else just process it.
        if curses.ascii.isdigit(ch):
            digits = self.gather() + chr(ch)
            candidates = links.disambiguate(digits, max_digits)
            if len(candidates) == 1:
                raise TerminateCommandInterrupt(candidates[0])
            return ch
        # If not a digit but a printable character, ignore it.
        if curses.ascii.isprint(ch):
            return 0
        # Everything else could be a control character and should be processed.
        return ch


class EscapeCommandInterrupt(Exception):
    """Signal that ESC has been pressed during command line."""
    pass


class TerminateCommandInterrupt(Exception):
    """Signal that validation ended command line input early.

    The value to use is stored in the command attribute. This value can be of
    any type: str for common commands but also int for ID input, etc.
    """

    def __init__(self, command, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command
