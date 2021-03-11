"""Single Gemini page curses management."""

import curses

from bebop.gemtext import parse_gemtext
from bebop.rendering import format_elements, render_lines


class Page:
    """Window containing page content."""

    MAX_COLS = 1000

    def __init__(self, initial_num_lines):
        self.dim = (initial_num_lines, Page.MAX_COLS)
        self.pad = curses.newpad(*self.dim)
        self.pad.scrollok(True)
        self.pad.idlok(True)
        self.metalines = []
        self.current_line = 0
        self.current_column = 0
        self.links = {}

    def show_gemtext(self, gemtext: bytes):
        """Render Gemtext data in the content pad."""
        elements = parse_gemtext(gemtext)
        self.metalines = format_elements(elements, 80)
        self.links = {
            meta["link_id"]: meta["url"]
            for meta, _ in self.metalines
            if "link_id" in meta and "url" in meta
        }
        self.pad.clear()
        self.dim = render_lines(self.metalines, self.pad, Page.MAX_COLS)
        self.current_line = 0
        self.current_column = 0

    def refresh_content(self, x, y):
        """Refresh content pad's view using the current line/column."""
        if x <= 0 or y <= 0:
            return
        content_position = self.current_line, self.current_column
        self.pad.refresh(*content_position, 0, 0, x, y)

    def scroll_v(self, num_lines: int, window_height: int =0):
        """Make the content pad scroll up and down by num_lines.

        Arguments:
        - num_lines: amount of lines to scroll, can be negative to scroll up.
        - window_height: total window height, used to limit scrolling down.

        Returns:
        True if scrolling occured and the pad has to be refreshed.
        """
        if num_lines < 0:
            num_lines = -num_lines
            min_line = 0
            if self.current_line > min_line:
                self.current_line = max(self.current_line - num_lines, min_line)
                return True
        else:
            max_line = self.dim[0] - window_height
            if self.current_line < max_line:
                self.current_line = min(self.current_line + num_lines, max_line)
                return True
        return False

    def scroll_h(self, num_columns: int, window_width: int =0):
        if num_columns < 0:
            num_columns = -num_columns
            min_column = 0
            if self.current_column > min_column:
                new_column = self.current_column - num_columns
                self.current_column = max(new_column, min_column)
                return True
        else:
            max_column = self.dim[1] - window_width
            if self.current_column < max_column:
                new_column = self.current_column + num_columns
                self.current_column = min(new_column, max_column)
                return True
        return False

    def go_to_beginning(self):
        if self.current_line:
            self.current_line = 0
            return True
        return False

    def go_to_end(self, window_height):
        max_line = self.dim[0] - window_height
        if self.current_line != max_line:
            self.current_line = max_line
            return True
        return False
