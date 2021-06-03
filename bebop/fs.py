"""Retrieve some paths from filesystem.

A lot of logic comes from `appdirs`:
https://github.com/ActiveState/appdirs/blob/master/appdirs.py
"""

from functools import lru_cache
from os import getenv
from os.path import expanduser
from pathlib import Path
from typing import Optional


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
    """Return the user downloads directory path (fallbacks to home dir)."""
    xdg_config_path = Path(getenv("XDG_CONFIG_HOME", expanduser("~/.config")))
    download_path = ""
    try:
        with open(xdg_config_path / "user-dirs.dirs", "rt") as user_dirs_file:
            for line in user_dirs_file:
                if line.startswith("XDG_DOWNLOAD_DIR="):
                    download_path = line.rstrip().split("=", maxsplit=1)[1]
                    download_path = download_path.strip('"')
                    home = expanduser("~")
                    download_path = download_path.replace("$HOME", home)
                    return Path(download_path)
    except OSError:
        pass
    return Path.home()


@lru_cache(None)
def get_identities_list_path() -> Path:
    """Return the identities JSON file path."""
    return get_user_data_path() / "identities.json"


@lru_cache(None)
def get_identities_path() -> Path:
    """Return the directory where identities are stored."""
    return get_user_data_path() / "identities"


@lru_cache(None)
def get_capsule_prefs_path() -> Path:
    """Return the directory where identities are stored."""
    return get_user_data_path() / "capsule_prefs.json"


@lru_cache(None)
def get_history_path() -> Path:
    """Return the saved history path."""
    return get_user_data_path() / "history.txt"


def ensure_bebop_files_exist() -> Optional[str]:
    """Ensure various Bebop's files or directories are present.

    Returns:
    None if all files and directories are present, an error string otherwise.
    """
    try:
        # Ensure the user data directory exists.
        user_data_path = get_user_data_path()
        if not user_data_path.exists():
            user_data_path.mkdir(parents=True)
        # Ensure the identities file and directory exists.
        identities_file_path = get_identities_list_path()
        if not identities_file_path.exists():
            with open(identities_file_path, "wt") as identities_file:
                identities_file.write("{}")
        identities_path = get_identities_path()
        if not identities_path.exists():
            identities_path.mkdir(parents=True)
        # Ensure the capsule preferences file exists.
        capsule_prefs_path = get_capsule_prefs_path()
        if not capsule_prefs_path.exists():
            with open(capsule_prefs_path, "wt") as prefs_file:
                prefs_file.write("{}")
    except OSError as exc:
        return str(exc)
