"""Single Gemini page curses management."""

import curses

from bebop.page import Page
from bebop.rendering import render_lines


class PagePad:
    """Window containing page content."""

    MAX_COLS = 1000

    def __init__(self, initial_num_lines):
        self.dim = (initial_num_lines, PagePad.MAX_COLS)
        self.pad = curses.newpad(*self.dim)
        self.pad.scrollok(True)
        self.pad.idlok(True)
        self.current_line = 0
        self.current_column = 0
        self.current_page = None

    def show_page(self, page: Page):
        """Render Gemtext data in the content pad."""
        self.current_page = page
        self.pad.clear()
        self.dim = render_lines(page.metalines, self.pad, PagePad.MAX_COLS)
        self.current_line = 0
        self.current_column = 0

    def refresh_content(self, x, y):
        """Refresh content pad's view using the current line/column."""
        if x <= 0 or y <= 0:
            return
        content_position = self.current_line, self.current_column
        try:
            self.pad.refresh(*content_position, 0, 0, x, y)
        except curses.error:
            pass

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
        """Make the content pad scroll left and right by num_columns.

        Arguments:
        - num_columns: amount of columns to scroll, can be negative to scroll
          left.
        - window_width: total window width, used to limit scrolling right.

        Returns:
        True if scrolling occured and the pad has to be refreshed.
        """
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
        """Make the pad show its start; return True if a refresh is needed."""
        if self.current_line:
            self.current_line = 0
            return True
        return False

    def go_to_end(self, window_height):
        """Make the pad show its bottom; return True if a refresh is needed."""
        max_line = self.get_max_line(window_height)
        if self.current_line != max_line:
            self.current_line = max_line
            return True
        return False

    def go_to_first_column(self):
        """Move to the first column; return True if a refresh is needed."""
        if self.current_column:
            self.current_column = 0
            return True
        return False

    def get_max_line(self, window_height):
        """Return the max line that can be used as current_line."""
        return self.dim[0] - window_height
