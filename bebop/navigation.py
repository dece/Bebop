"""URI (RFC 3986) helpers for Gemini navigation.

It was supposed to be just thin fixes around urllib.parse functions but as
gemini is not recognized as a valid scheme it breaks a lot of things, so it
turned into a basic re-implementation of the RFC.
"""

import re
from typing import Any, Dict, Optional
from urllib.parse import quote


URI_RE = re.compile(
    "^"
    r"(?:(?P<scheme>[^:/?#\n]+):)?"
    r"(?://(?P<netloc>[^/?#\n]*))?"
    r"(?P<path>[^?#\n]*)"
    r"(?:\?(?P<query>[^#\n]*))?"
    r"(?:#(?P<fragment>.*))?"
    "$"
)

NO_NETLOC_SCHEMES = ("bebop",)


class InvalidUrlException(Exception):
    """Generic exception for invalid URLs used in this module."""

    def __init__(self, url):
        super().__init__()
        self.url = url


def parse_url(url: str, default_scheme: Optional[str] =None) -> Dict[str, Any]:
    """Return URL parts from this URL.

    Use the RFC regex to get parts from URL. This function can be used on
    regular URLs but also on not-so-compliant URLs, e.g. "capsule.org/page",
    which might be typed by an user (see `absolute` argument).

    Arguments:
    - url: URL to parse.
    - default_scheme: specify the scheme to use if the URL either does not
      specify it and we need it (e.g. there is a location).

    Returns:
    URL parts, as a dictionary with the following keys: "scheme", "netloc",
    "path", "query" and "fragment". All keys are present, but all values can be
    None, except path which is always a string (but can be empty).

    Raises:
    InvalidUrlException if you put really really stupid strings in there.
    """
    match = URI_RE.match(url)
    if not match:
        raise InvalidUrlException(url)

    match_dict = match.groupdict()
    parts = {
        k: match_dict.get(k)
        for k in ("scheme", "netloc", "path", "query", "fragment")
    }

    # Smol hack: if there is no scheme, use `default_scheme` as default.
    if default_scheme and parts["scheme"] is None:
        parts["scheme"] = default_scheme

    return parts


def unparse_url(parts) -> str:
    """Unparse parts of an URL produced by `parse_url`."""
    url = ""
    if parts["scheme"] is not None:
        url += parts["scheme"] + ":"
    if parts["netloc"] is not None:
        url += "//" + parts["netloc"]
    if parts["path"] is not None:
        url += parts["path"]
    if parts["query"] is not None:
        url += "?" + parts["query"]
    if parts["fragment"] is not None:
        url += "#" + parts["fragment"]
    return url


def clear_post_path(parts) -> None:
    """Clear optional post-path parts (query and fragment)."""
    parts["query"] = None
    parts["fragment"] = None


def join_url(base_url: str, rel_url: str) -> str:
    """Join a base URL with a relative path."""
    parts = parse_url(base_url)
    rel_parts = parse_url(rel_url)
    if rel_url.startswith("/"):
        new_path = rel_parts["path"]
    else:
        base_path = parts["path"] or ""
        new_path = remove_last_segment(base_path) + "/" + rel_parts["path"]
    parts["path"] = remove_dot_segments(new_path)
    parts["query"] = rel_parts["query"]
    parts["fragment"] = rel_parts["fragment"]
    return unparse_url(parts)


def remove_dot_segments(path: str):
    """Remove dot segments in an URL path."""
    output = ""
    while path:
        if path.startswith("../"):
            path = path[3:]
        elif path.startswith("./") or path.startswith("/./"):
            path = path[2:]  # Either strip "./" or leave a single "/".
        elif path == "/.":
            path = "/"
        elif path.startswith("/../"):
            path = "/" + path[4:]
            output = remove_last_segment(output)
        elif path == "/..":
            path = "/"
            output = remove_last_segment(output)
        elif path in (".", ".."):
            path = ""
        else:
            first_segment, path = pop_first_segment(path)
            output += first_segment
    return output


def remove_last_segment(path: str):
    """Remove last path segment, including preceding "/" if any."""
    return path[:path.rfind("/")]


def pop_first_segment(path: str):
    """Return first segment and the rest.

    Return the first segment including the initial "/" if any, and the rest of
    the path up to, but not including, the next "/" or the end of the string.
    """
    next_slash = path[1:].find("/")
    if next_slash == -1:
        return path, ""
    next_slash += 1
    return path[:next_slash], path[next_slash:]


def set_parameter(url: str, user_input: str) -> str:
    """Return a new URL with the escaped user input appended."""
    parts = parse_url(url)
    parts["query"] = quote(user_input)
    return unparse_url(parts)


def get_parent_path(path: str) -> str:
    """Return the parent path."""
    last_slash = path.rstrip("/").rfind("/")
    if last_slash > -1:
        path = path[:last_slash + 1]
    return path


def get_parent_url(url: str) -> str:
    """Return the parent URL (one level up)."""
    parts = parse_url(url)
    parts["path"] = get_parent_path(parts["path"])  # type: ignore
    clear_post_path(parts)
    return unparse_url(parts)


def get_root_url(url: str) -> str:
    """Return the root URL (basically discards path)."""
    parts = parse_url(url)
    parts["path"] = "/"
    clear_post_path(parts)
    return unparse_url(parts)


def parse_host_and_port(host: str, default_port: int):
    """Return the host and port from a "host:port" string."""
    if ":" in host:
        host, port = host.split(":", maxsplit=1)
        try:
            port = int(port)
        except ValueError:
            return None
    else:
        port = default_port
    return host, port
