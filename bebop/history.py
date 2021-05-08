"""History management."""


class History:
    """Basic browsing history manager.

    The history follows the "by last visited" behaviour of Firefox for the lack
    of a better idea. Links are pushed as they are visited. If a link is visited
    again, it bubbles up to the top of the history.
    """

    def __init__(self):
        self.urls = []

    def push(self, url):
        """Add an URL to the history.

        If the URL is already in the list, it is moved to the top.
        """
        try:
            self.urls.remove(url)
        except ValueError:
            pass
        self.urls.append(url)

    def get_previous(self):
        """Return previous URL, or None if there is only one or zero URL."""
        try:
            return self.urls[-2]
        except IndexError:
            return None

    def to_gemtext(self):
        """Generate a simple Gemtext page of the current history."""
        return "\n".join("=> " + url for url in self.urls)
