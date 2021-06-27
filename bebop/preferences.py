"""Per-capsule preferences.

Currently contains only overrides for render modes, per URL path. In the future
it may be interesting to move a few things from the config to here, such as the
text width.

This is a map from URLs to dicts. The only used key is render_mode.
"""

import json
import logging
from pathlib import Path
from typing import Optional


def load_capsule_prefs(prefs_path: Path) -> Optional[dict]:
    """Return saved capsule preferences or None on error."""
    prefs = {}
    try:
        with open(prefs_path, "rt") as prefs_file:
            prefs = json.load(prefs_file)
    except (OSError, ValueError) as exc:
        logging.error(f"Failed to load capsule prefs '{prefs_path}': {exc}")
        return None
    return prefs


def save_capsule_prefs(prefs: dict, prefs_path: Path) -> bool:
    """Save the capsule preferences. Return True on success."""
    try:
        with open(prefs_path, "wt") as prefs_file:
            json.dump(prefs, prefs_file, indent=2)
    except (OSError, ValueError) as exc:
        logging.error(f"Failed to save capsule prefs '{prefs_path}': {exc}")
        return False
    return True


def get_url_render_mode_pref(prefs: dict, url: str) -> Optional[str]:
    """Return the desired render mode for this URL.

    If the preferences contain the URL or a parent URL, the corresponding render
    mode is used. If several URLs are prefixes of the `url` argument, the
    longest one is used to get the matching preference.

    Arguments:
    - prefs: current capsule preferences.
    - url: URL about to be rendered.
    """
    prefix_urls = []
    for key in prefs:
        if url.startswith(key):
            prefix_urls.append(key)
    if not prefix_urls:
        return None
    key = max(prefix_urls, key=len)
    preference = prefs[key]
    return preference.get("render_mode")
