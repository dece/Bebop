"""History management."""


class History:
    """Basic browsing history manager."""

    def __init__(self):
        self.urls = []

    def has_links(self):
        """Return True if there is at least one URL in the history."""
        return bool(self.urls)

    def push(self, url):
        """Add an URL to the history."""
        if not self.urls or self.urls[-1] != url:
            self.urls.append(url)

    def pop(self):
        """Return latest URL added to history and remove it."""
        return self.urls.pop()
