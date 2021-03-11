"""Integrated command-line implementation."""
import curses
import curses.textpad


class CommandLine:

    def __init__(self, window):
        self.window = window
        self.textbox = None

    def clear(self):
        self.window.clear()
        self.window.refresh()

    def focus(self, command_char, validator=None, prefix=""):
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
        self.window.clear()
        self.window.refresh()
        self.textbox = curses.textpad.Textbox(self.window)
        self.window.addstr(command_char + prefix)
        curses.curs_set(1)
        try:
            command = self.textbox.edit(validator)[1:].strip()
        except EscapeCommandInterrupt:
            command = ""
        except TerminateCommandInterrupt as exc:
            command = exc.command
        curses.curs_set(0)
        self.window.clear()
        self.window.refresh()
        return command

    def gather(self):
        """Return the string currently written by the user in command line."""
        return self.textbox.gather()[1:].rstrip()


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
