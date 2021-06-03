"""History management."""

import logging

from bebop.fs import get_history_path


class History:
    """Basic browsing history manager."""

    def __init__(self, limit):
        self.urls = []
        self.backlist = []
        self.limit = limit

    def push(self, url):
        """Add an URL to the history."""
        # Append url to our URLs, bubbling it up if it's already there.
        try:
            self.urls.remove(url)
        except ValueError:
            pass
        self.urls.append(url)
        if len(self.urls) > self.limit:
            self.urls.pop(0)

        # Also simply push it to the backlist.
        self.backlist.append(url)
        if len(self.backlist) > self.limit:
            self.backlist.pop(0)

    def get_previous(self, actual_previous=False):
        """Return previous URL, or None if there is only one or zero URL."""
        try:
            if actual_previous:
                return self.backlist[-1]
            # The backlist should be populated with the first link visited and
            # never completely emptied afterwards, or we end up in situation
            # where you can't get away from internal pages.
            if len(self.backlist) > 1:
                self.backlist.pop()
            return self.backlist[-1]
        except IndexError:
            return None

    def to_gemtext(self):
        """Generate a simple Gemtext page of the current history.

        Present a page that follows the "by last visited" behaviour of Firefox
        for the lack of a better idea, avoiding duplicated entries.
        """
        urls = []
        seen = set()
        for url in reversed(self.urls):
            if url in seen:
                continue
            urls.append(url)
            seen.add(url)
        return "# History\n\n" + "\n".join("=> " + url for url in urls)

    def save(self):
        """Save current history to user data."""
        history_path = get_history_path()
        try:
            with open(history_path, "wt") as history_file:
                for url in self.urls:
                    history_file.write(url + "\n")
        except OSError as exc:
            logging.error(f"Failed to save history {history_path}: {exc}")
            return False
        return True

    def load(self):
        """Load saved history from user data."""
        history_path = get_history_path()
        self.urls = []
        try:
            with open(history_path, "rt") as history_file:
                for url in history_file:
                    self.urls.append(url.rstrip())
        except OSError as exc:
            logging.error(f"Failed to load history {history_path}: {exc}")
            return False
        return True
