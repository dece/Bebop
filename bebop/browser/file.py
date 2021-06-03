"""Local files browser."""

import logging
from pathlib import Path

from bebop.browser.browser import Browser
from bebop.page import Page


def open_file(browser: Browser, filepath: str, encoding="utf-8"):
    """Open a file and render it.

    This should be used only on Gemtext files or at least text files.
    Anything else will produce garbage and may crash the program. In the
    future this should be able to use a different parser according to a MIME
    type or something.

    Arguments:
    - browser: Browser object making the request.
    - filepath: a text file path on disk.
    - encoding: file's encoding.

    Returns:
    The loaded file URI on success, None otherwise (e.g. file not found).
    """
    path = Path(filepath)
    if not path.exists():
        logging.error(f"File {filepath} does not exist.")
        return None

    if path.is_file():
        try:
            with open(filepath, "rt", encoding=encoding) as f:
                text = f.read()
        except (OSError, ValueError) as exc:
            browser.set_status_error(f"Failed to open file: {exc}")
            return None
        browser.load_page(Page.from_text(text))
    elif path.is_dir():
        gemtext = filepath + "\n\n"
        for entry in sorted(path.iterdir()):
            name = entry.name
            if entry.is_dir():
                name += "/"
            gemtext += f"=> {entry} {name}\n"
        wrap_at = browser.config["text_width"]
        browser.load_page(Page.from_gemtext(gemtext, wrap_at))
    file_url = "file://" + filepath
    browser.current_url = file_url
    return file_url
