"""Plugin management.

Plugins are here to allow extending Bebop with additional features, potentially
requiring external libraries, without requiring users who just want a Gemini
browser to install anything.

Support for plugins is very simple right now: a plugin can only register an URL
scheme to handle.
"""

from abc import ABC, abstractmethod
from typing import Optional

from bebop.browser.browser import Browser


class SchemePlugin(ABC):
    """Plugin for URL scheme management."""

    def __init__(self, scheme: str) -> None:
        self.scheme = scheme

    @abstractmethod
    def open_url(self, browser: Browser, url: str) -> Optional[str]:
        """Handle an URL for this scheme.

        Returns:
        The properly handled URL at the end of this query, which may be
        different from the url parameter if redirections happened, or None if an
        error happened.
        """
        raise NotImplementedError
