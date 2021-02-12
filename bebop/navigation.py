import re
import urllib.parse


def parse_url(url, absolute=False):
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
    if url.startswith("gemini://"):
        url = url[7:]
    parts = urllib.parse.urlparse(url, scheme="gemini")
    if not parts.netloc and absolute:
        parts = urllib.parse.urlparse(f"//{url}", scheme="gemini")
    return parts


def join_url(base_url, url):
    """Join a base URL with a relative url."""
    if base_url.startswith("gemini://"):
        base_url = base_url[7:]
    parts = parse_url(urllib.parse.urljoin(base_url, url))
    return urllib.parse.urlunparse(parts)
