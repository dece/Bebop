"""Retrieve some paths from filesystem.

A lot of logic comes from `appdirs`:
https://github.com/ActiveState/appdirs/blob/master/appdirs.py
"""

from os import getenv
from os.path import expanduser, join


APP_NAME = "bebop"


def get_user_data_dir():
    """Return the user data directory."""
    path = getenv("XDG_DATA_HOME", expanduser("~/.local/share"))
    path = join(path, APP_NAME)
    return path
