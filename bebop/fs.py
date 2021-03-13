"""Retrieve some paths from filesystem.

A lot of logic comes from `appdirs`:
https://github.com/ActiveState/appdirs/blob/master/appdirs.py
"""

from os import getenv
from os.path import expanduser
from pathlib import Path


APP_NAME = "bebop"


def get_user_data_path() -> Path:
    """Return the user data directory path."""
    path = Path(getenv("XDG_DATA_HOME", expanduser("~/.local/share")))
    return path / APP_NAME
