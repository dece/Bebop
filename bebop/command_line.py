"""Integrated command-line implementation."""

import curses
import curses.ascii
import os
import logging
import tempfile
from typing import Optional

from bebop.external import open_external_program
from bebop.links import Links
from bebop.textbox import Textbox


class CommandLine:
    """Basic and flaky command-line à la Vim, using curses module's Textbox.

    I don't understand how to get proper pad-like behaviour, e.g. to scroll past
    the window's right border when writing more content than the width allows.
    Therefore I just added the M-e keybind to call an external editor and use
    its content as result.

    Attributes:
    - window: curses window to use for the command line and Textbox.
    - editor_command: external command to use to edit content externally.
    - textbox: Textbox object handling user input.
    """

    CHAR_COMMAND = ":"
    CHAR_DIGIT = "&"
    CHAR_TEXT = ">"

    def __init__(self, window, editor_command):
        self.window = window
        self.editor_command = editor_command
        self.textbox = Textbox(self.window, insert_mode=True)

    def clear(self):
        """Clear command-line contents."""
        self.window.clear()
        self.window.refresh()

    def gather(self) -> str:
        """Return the string currently written by the user in command line.

        This doesn't count the command char used, but it includes then prefix.
        Trailing whitespace is trimmed.
        """
        return self.textbox.gather()[1:].rstrip()

    def focus(
        self,
        command_char,
        validator=None,
        prefix="",
        escape_to_none=False
    ) -> Optional[str]:
        """Give user focus to the command bar.

        Show the command char and give focus to the command textbox. The
        validator function is passed to the textbox.

        Arguments:
        - command_char: char to display before the command line; it must be an
          str of length 1, else the return value of `gather` might be wrong.
        - validator: function to use to validate the input chars; if omitted,
          `validate_common_input` is used.
        - prefix: string to insert before the cursor in the command line.
        - escape_to_none: if True, an escape interruption returns None instead
          of an empty string.

        Returns:
        User input as string. The string will be empty if the validator raised
        an EscapeInterrupt, unless `escape_to_none` is True.
        """
        validator = validator or self._validate_common_input
        self.window.clear()
        self.window.refresh()
        self.window.addstr(command_char + prefix)
        curses.curs_set(1)
        try:
            command = self.textbox.edit(validator)
        except EscapeCommandInterrupt:
            command = "" if not escape_to_none else None
        except TerminateCommandInterrupt as exc:
            command = exc.command
        else:
            command = command[1:].rstrip()
        curses.curs_set(0)
        self.clear()
        return command

    def _validate_common_input(self, ch: int):
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
            _, x = self.textbox.win.getyx()
            if x == 1:
                raise EscapeCommandInterrupt()
            pass
        elif ch == curses.ascii.ESC:  # Could be ESC or ALT
            self.window.nodelay(True)
            ch = self.window.getch()
            self.window.nodelay(False)
            if ch == -1:
                raise EscapeCommandInterrupt()
            else:  # ALT keybinds.
                if ch == ord("e"):
                    self.open_editor(self.gather())
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
        validator = lambda ch: self._validate_link_digit(ch, links, max_digits)
        link_input = self.focus(CommandLine.CHAR_DIGIT, validator, digit)
        if not link_input:
            return 1, None
        try:
            link_id = int(link_input)
        except ValueError:
            return 2, f"Invalid link ID {link_input}."
        return 0, link_id

    def _validate_link_digit(self, ch: int, links: Links, max_digits: int):
        """Handle input chars to be used as link ID."""
        # Handle common chars.
        ch = self._validate_common_input(ch)
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

    def open_editor(self, existing_content=None):
        """Open an external editor and raise termination interrupt."""
        try:
            with tempfile.NamedTemporaryFile("w+t", delete=False) as temp_file:
                if existing_content:
                    temp_file.write(existing_content)
                temp_filepath = temp_file.name
        except OSError:
            logging.error("Could not open or write to temporary file.")
            return

        command = self.editor_command + [temp_filepath]
        success = open_external_program(command)
        if not success:
            return

        try:
            with open(temp_filepath, "rt") as temp_file:
                content = temp_file.read().rstrip("\r\n")
            os.unlink(temp_filepath)
        except OSError:
            logging.error("Could not read temporary file after user edition.")
            return
        raise TerminateCommandInterrupt(content)

    def prompt_key(self, keys):
        """Focus the command line and wait for the user """
        validator = lambda ch: self._validate_prompt(ch, keys)
        key = self.focus(CommandLine.CHAR_TEXT, validator)
        return key if key in keys else ""

    def _validate_prompt(self, ch: int, keys):
        """Handle input chars and raise a terminate interrupt on a valid key."""
        # Handle common keys.
        ch = self._validate_common_input(ch)
        try:
            char = chr(ch)
        except ValueError:
            pass
        else:
            if char in keys:
                raise TerminateCommandInterrupt(char)
        return 0


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
