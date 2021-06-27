"""Local files browser."""

import logging
from pathlib import Path
from urllib.parse import quote, unquote

from bebop.browser.browser import Browser
from bebop.page import Page, get_render_options


def open_file(browser: Browser, filepath: str, encoding="utf-8"):
    """Open a file and render it.

    This should be used only text files or directories. Anything else will
    produce garbage and may crash the program. In the future this should be able
    to use a different parser according to a MIME type or something.

    Arguments:
    - browser: Browser object making the request.
    - filepath: a text file path on disk.
    - encoding: file's encoding.

    Returns:
    The loaded file URI on success, None otherwise (e.g. file not found).
    """
    path = Path(unquote(filepath))
    if not path.exists():
        logging.error(f"File {path} does not exist.")
        return None

    if path.is_file():
        try:
            with open(path, "rt", encoding=encoding) as f:
                text = f.read()
        except (OSError, ValueError) as exc:
            browser.set_status_error(f"Failed to open file: {exc}")
            return None
        if path.suffix == ".gmi":
            page = Page.from_gemtext(text, get_render_options(browser.config))
        else:
            page = Page.from_text(text)
        browser.load_page(page)
    elif path.is_dir():
        gemtext = str(path) + "\n\n"
        for entry in sorted(path.iterdir()):
            entry_path = quote(str(entry.absolute()))
            name = entry.name
            if entry.is_dir():
                name += "/"
            gemtext += f"=> {entry_path} {name}\n"
        render_opts = get_render_options(browser.config)
        browser.load_page(Page.from_gemtext(gemtext, render_opts))
    file_url = f"file://{path}"
    browser.current_url = file_url
    return file_url
