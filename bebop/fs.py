"""Retrieve some paths from filesystem.

A lot of logic comes from `appdirs`:
https://github.com/ActiveState/appdirs/blob/master/appdirs.py
"""

from functools import lru_cache
from os import getenv
from os.path import expanduser
from pathlib import Path


APP_NAME = "bebop"


@lru_cache(None)
def get_config_path() -> Path:
    """Return the user config file path."""
    config_dir = Path(getenv("XDG_CONFIG_HOME", expanduser("~/.config")))
    return config_dir / (APP_NAME + ".json")


@lru_cache(None)
def get_user_data_path() -> Path:
    """Return the user data directory path."""
    path = Path(getenv("XDG_DATA_HOME", expanduser("~/.local/share")))
    return path / APP_NAME


@lru_cache(None)
def get_downloads_path() -> Path:
    """Return the user downloads directory path."""
    xdg_config_path = Path(getenv("XDG_CONFIG_HOME", expanduser("~/.config")))
    download_path = ""
    try:
        with open(xdg_config_path / "user-dirs.dirs", "rt") as user_dirs_file:
            for line in user_dirs_file:
                if line.startswith("XDG_DOWNLOAD_DIR="):
                    download_path = line.rstrip().split("=", maxsplit=1)[1]
                    download_path = download_path.strip('"')
                    download_path = download_path.replace("$HOME", expanduser("~"))
                    break
    except OSError:
        pass
    if download_path:
        return Path(download_path)
    return Path.home()
