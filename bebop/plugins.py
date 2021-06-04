"""Plugin management.

Plugins are here to allow extending Bebop with additional features, potentially
requiring external libraries, without requiring users who just want a Gemini
browser to install anything.

Support for plugins is very simple right now: a plugin can only register an URL
scheme to handle.

To create a plugin, follow these steps:

- Implement a class inheriting one of the plugin classes from this module.
- Put it in package named `bebop_<plugin-name>`.
- Make this module export a `plugin` variable which is a plugin instance.
- Put the plugin name in `enabled_plugins` config to load on next start.

There is at least one plugin in this repository in the `plugins` directory.
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
