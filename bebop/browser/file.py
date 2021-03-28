"""Local files browser."""

from bebop.browser.browser import Browser
from bebop.page import Page


def open_file(browser: Browser, filepath: str, encoding="utf-8", history=True):
    """Open a file and render it.

    This should be used only on Gemtext files or at least text files.
    Anything else will produce garbage and may crash the program. In the
    future this should be able to use a different parser according to a MIME
    type or something.
    """
    try:
        with open(filepath, "rt", encoding=encoding) as f:
            text = f.read()
    except (OSError, ValueError) as exc:
        browser.set_status_error(f"Failed to open file: {exc}")
        return
    browser.load_page(Page.from_gemtext(text))
    file_url = "file://" + filepath
    if history:
        browser.history.push(file_url)
    browser.current_url = file_url
