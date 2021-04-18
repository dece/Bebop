"""Gemini-related features of the browser."""

from pathlib import Path

from bebop.browser.browser import Browser
from bebop.command_line import CommandLine
from bebop.fs import get_downloads_path
from bebop.navigation import set_parameter
from bebop.page import Page
from bebop.protocol import Request, Response


MAX_URL_LEN = 1024


def open_gemini_url(browser: Browser, url, redirects=0, history=True,
                    use_cache=True):
    """Open a Gemini URL and set the formatted response as content.

    After initiating the connection, TODO
    """
    if len(url) >= MAX_URL_LEN:
        browser.set_status_error(f"Request URL too long.")
        return

    browser.set_status(f"Loading {url}")

    if use_cache and url in browser.cache:
        browser.load_page(browser.cache[url])
        if browser.current_url and history:
            browser.history.push(browser.current_url)
        browser.current_url = url
        browser.set_status(url)
        return

    req = Request(url, browser.stash)
    connect_timeout = browser.config["connect_timeout"]
    connected = req.connect(connect_timeout)
    if not connected:
        if req.state == Request.STATE_ERROR_CERT:
            error = f"Certificate was missing or corrupt ({url})."
        elif req.state == Request.STATE_UNTRUSTED_CERT:
            error = f"Certificate has been changed ({url})."
            # TODO propose the user ways to handle this.
        elif req.state == Request.STATE_CONNECTION_FAILED:
            error_details = ": " + req.error if req.error else "."
            error = f"Connection failed ({url})" + error_details
        else:
            error = f"Connection failed ({url})."
        browser.set_status_error(error)
        return

    if req.state == Request.STATE_INVALID_CERT:
        # TODO propose abort / temp trust
        pass
    elif req.state == Request.STATE_UNKNOWN_CERT:
        # TODO propose abort / temp trust / perm trust
        pass
    else:
        pass # TODO

    data = req.proceed()
    if not data:
        browser.set_status_error(f"Server did not respond in time ({url}).")
        return
    response = Response.parse(data)
    if not response:
        browser.set_status_error(f"Server response parsing failed ({url}).")
        return

    _handle_response(browser, response, url, redirects, history)


def _handle_response(browser: Browser, response: Response, url: str,
                     redirects: int, history: bool):
    """Handle a response from a Gemini server."""
    if response.code == 20:
        _handle_successful_response(browser, response, url, history)
    elif response.generic_code == 30 and response.meta:
        browser.open_url(response.meta, base_url=url, redirects=redirects + 1)
    elif response.generic_code in (40, 50):
        error = f"Server error: {response.meta or Response.code.name}"
        browser.set_status_error(error)
    elif response.generic_code == 10:
        _handle_input_request(browser, url, response.meta)
    else:
        error = f"Unhandled response code {response.code}"
        browser.set_status_error(error)


def _handle_successful_response(browser: Browser, response: Response, url: str,
                                history: bool):
    """Handle a successful response content from a Gemini server.

    According to the MIME type received or inferred, the response is either
    rendered by the browser, or saved to disk. If an error occurs, the browser
    displays it.

    Only text content is rendered. For Gemini, the encoding specified in the
    response is used, if available on the Python distribution. For other text
    formats, only UTF-8 is attempted.

    Arguments:
    - browser: Browser instance that made the initial request.
    - url: original URL.
    - response: a successful Response.
    - history: whether to modify history on a page load.
    """
    mime_type = response.get_mime_type()
    page = None
    error = None
    filepath = None
    if mime_type.main_type == "text":
        if mime_type.sub_type == "gemini":
            encoding = mime_type.charset
            try:
                text = response.content.decode(encoding, errors="replace")
            except LookupError:
                error = f"Unknown encoding {encoding}."
            else:
                page = Page.from_gemtext(text, browser.config["text_width"])
        else:
            text = response.content.decode("utf-8", errors="replace")
            page = Page.from_text(text)
    else:
        filepath = _get_download_path(url)

    if page:
        browser.load_page(page)
        if browser.current_url and history:
            browser.history.push(browser.current_url)
        browser.current_url = url
        browser.cache[url] = page
        browser.set_status(url)
    elif filepath:
        try:
            with open(filepath, "wb") as download_file:
                download_file.write(response.content)
        except OSError as exc:
            browser.set_status_error(f"Failed to save {url} ({exc})")
        else:
            browser.set_status(f"Downloaded {url} ({mime_type.short}).")
    elif error:
        browser.set_status_error(error)


def _get_download_path(url: str) -> Path:
    """Try to find the best download file path possible from this URL."""
    download_dir = get_downloads_path()
    url_parts = url.rsplit("/", maxsplit=1)
    if url_parts:
        filename = url_parts[-1]
    else:
        filename = url.split("://")[1] if "://" in url else url
        filename = filename.replace("/", "_")
    return download_dir / filename


def _handle_input_request(browser: Browser, from_url: str, message: str =None):
    """Focus command-line to pass input to the server."""
    if message:
        browser.set_status(f"Input needed: {message}")
    else:
        browser.set_status("Input needed:")
    user_input = browser.command_line.focus(CommandLine.CHAR_TEXT)
    if not user_input:
        return
    url = set_parameter(from_url, user_input)
    open_gemini_url(browser, url)
