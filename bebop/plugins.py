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
from dataclasses import dataclass
from typing import Optional

from bebop.browser.browser import Browser


@dataclass
class PluginCommand:
    """A descriptor for a plugin command.

    Attributes:
    - name: the command name.
    - description: a very short description of the command; should start lower
      case and does not need a period at the end.
    """
    name: str
    description: str


class Plugin(ABC):
    """Base class for plugins.

    Attributes:
    - commands: list of PluginCommand provided by the plugin.
    """

    def __init__(self) -> None:
        super().__init__()
        self.commands = []

    def use_command(self, browser: Browser, name: str, text: str):
        """Use a command presented by this plugin.

        Plugins that do not use custom commands can leave this method
        unimplemented.

        Attributes:
        - name: the command used as it is in the commands list.
        - text: the whole command text, including the command name.
        """
        pass


class SchemePlugin(Plugin):
    """Plugin for URL scheme management.

    If you want to create a plugin that can handle new schemes, create a plugin
    inheriting this class.
    """

    def __init__(self, scheme: str) -> None:
        super().__init__()
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
