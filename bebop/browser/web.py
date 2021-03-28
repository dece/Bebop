"""Ha! You thought there would be a Web browser in there?"""

import webbrowser

from bebop.browser.browser import Browser


def open_web_url(browser: Browser, url):
    """Open a Web URL. Currently relies in Python's webbrowser module."""
    browser.set_status(f"Opening {url}")
    webbrowser.open_new_tab(url)
