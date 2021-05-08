"""Local files browser."""

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
    try:
        with open(filepath, "rt", encoding=encoding) as f:
            text = f.read()
    except (OSError, ValueError) as exc:
        browser.set_status_error(f"Failed to open file: {exc}")
        return None
    browser.load_page(Page.from_text(text))
    file_url = "file://" + filepath
    browser.current_url = file_url
    return file_url
