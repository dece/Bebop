"""URI (RFC 3986) helpers for Gemini navigation."""

import urllib.parse


def parse_url(url: str, absolute: bool =False):
    """Return URL parts from this URL.

    This uses urllib.parse.urlparse to not reinvent the wheel, with a few
    adjustments.

    First, urllib does not know the Gemini scheme (yet!) so if it
    is specified we strip it to get an absolute netloc.

    Second, as this function can be used to process arbitrary user input, we
    clean it a bit:
    - strip whitespaces from the URL
    - if "absolute" is True, consider that the URL is meant to be absolute, even
      though it technically is not, e.g. "dece.space" is not absolute as it
      misses either the // delimiter.
    """
    url = url.strip()
    if url.startswith("file://"):
        return urllib.parse.urlparse(url)
    if url.startswith("gemini://"):
        url = url[7:]
    parts = urllib.parse.urlparse(url, scheme="gemini")
    if not parts.netloc or absolute:
        parts = urllib.parse.urlparse(f"//{url}", scheme="gemini")
    return parts


def sanitize_url(url: str):
    """Parse and unparse an URL to ensure it has been properly formatted."""
    return urllib.parse.urlunparse(parse_url(url))


def join_url(base_url: str, url: str):
    """Join a base URL with a relative url."""
    if base_url.startswith("gemini://"):
        base_url = base_url[7:]
    parts = parse_url(urllib.parse.urljoin(base_url, url))
    return urllib.parse.urlunparse(parts)


def set_parameter(url: str, user_input: str):
    """Return a new URL with the escaped user input appended."""
    quoted_input = urllib.parse.quote(user_input)
    if "?" in url:
        url = url.split("?", maxsplit=1)[0]
    return url + "?" + quoted_input
