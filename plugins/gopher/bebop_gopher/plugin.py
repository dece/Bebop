import logging
import re
import socket
from enum import Enum
from typing import Optional

from bebop.browser.browser import Browser
from bebop.command_line import CommandLine
from bebop.downloads import get_download_path
from bebop.links import Links
from bebop.metalines import LineType
from bebop.mime import MimeType
from bebop.navigation import parse_url, parse_host_and_port, unparse_url
from bebop.page import Page
from bebop.plugins import PluginCommand, SchemePlugin


class ItemType(Enum):
    FILE = "0"
    DIR = "1"
    CCSO = "2"
    ERROR = "3"
    BINHEXED = "4"
    DOS = "5"
    UUENC = "6"
    SEARCH = "7"
    TELNET = "8"
    BINARY = "9"
    REDUNDANT = "+"
    TN3270 = "T"
    GIF = "g"
    IMAGE = "I"
    # These are not in the original RFC but encountered frequently.
    INFO = "i"
    DOC = "d"
    HTML = "h"
    SOUND = "s"
    _missing_ = lambda s: ItemType.FILE


# Types that can be parsed as a page (see `parse_source`).
PARSABLE_TYPES = (ItemType.FILE, ItemType.DIR)
# Types that are not rendered by this plugin; should be handled by a separate
# program, but for now we simply do nothing with them.
UNHANDLED_TYPES = (
    ItemType.CCSO, ItemType.ERROR, ItemType.TELNET, ItemType.REDUNDANT,
    ItemType.TN3270
)
# Map item types lowercase names to the actual type, to easily set a type from
# the command-line.
USER_FRIENDLY_TYPES = {t.name.lower(): t for t in ItemType}
# Icons to display for some item types in a Gopher map.
ICONS = {
    ItemType.FILE: "📄",
    ItemType.DIR: "📂",
    ItemType.SEARCH: "✍ ",
    ItemType.HTML: "🌐",
}


# This regex checks if the URL respects RFC 4266 and has an item type.
TYPE_PATH_RE = re.compile(r"^/([\d\+TgIidhs])(.*)")


class GopherPluginException(Exception):

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message


class GopherPlugin(SchemePlugin):

    def __init__(self) -> None:
        super().__init__("gopher")
        self.commands = [
            PluginCommand(
                "set-item-type",
                "display current page as another item type (Gopher only)"
            )
        ]

    def open_url(self, browser: Browser, url: str) -> Optional[str]:
        """Request an selector from a Gopher host.

        As Bebop works only with URLs and not really the Gopher host/selector
        format, we use RFC 4266 (“The gopher URI Scheme”) for consistency with
        other schemes and to get that sweet item type hint in the URL path.
        """
        parts = parse_url(url)
        host = parts["netloc"]
        host_and_port = parse_host_and_port(host, 70)
        if host_and_port is None:
            browser.set_status_error("Could not parse gopher URL.")
            return None
        host, port = host_and_port
        # Decode path; spaces in Gopher URLs are encoded for display in Bebop.
        path = parts["path"].replace("%20", " ")

        # If the URL has an item type, use it to properly parse the response.
        type_path_match = TYPE_PATH_RE.match(path)
        if type_path_match:
            item_type = ItemType(type_path_match.group(1))
            path = type_path_match.group(2)
            # Don't try to open a Telnet connection or other silly retro things.
            if item_type in UNHANDLED_TYPES:
                browser.set_status_error(f"Unhandled item {item_type.name}.")
                return None
            # Let user input some text for search items.
            if item_type == ItemType.SEARCH:
                user_input = browser.get_user_text_input(
                    "Input:",
                    CommandLine.CHAR_TEXT,
                    strip=True
                )
                if not user_input:
                    return None
                item_type = ItemType.DIR
                previous_search_index = path.find("%09")
                if previous_search_index > -1:
                    path = path[:previous_search_index]
                path = f"{path}\t{user_input}"
            # Note that we don't try to handle "h" items here because if the URL
            # actually uses http scheme, it should not end up in this plugin.
        else:
            item_type = ItemType.DIR

        # If we have spaces in our path, encode it for UI & logging.
        encoded_path = path.replace(" ", "%20").replace("\t", "%09")
        browser.set_status(f"Loading {host} {port} '{encoded_path}'…")

        timeout = browser.config["connect_timeout"]
        try:
            response = request(host, port, path, timeout)
        except GopherPluginException as exc:
            browser.set_status_error("Error: " + exc.message)
            return None

        url = f"gopher://{host}:{port}/{item_type.value}{encoded_path}"
        if item_type in PARSABLE_TYPES:
            page = parse_response(response, item_type)
            browser.load_page(page)
            browser.current_url = url
        else:
            download_dir = browser.config["download_path"]
            filepath = get_download_path(url, download_dir=download_dir)
            try:
                with open(filepath, "wb") as download_file:
                    download_file.write(response)
            except OSError as exc:
                browser.set_status_error(f"Failed to save {url} ({exc})")
                return None
            else:
                browser.set_status(f"Downloaded {url}.")
                browser.last_download = None, filepath

        return url

    def use_command(self, browser: Browser, name: str, text: str):
        if name == "set-item-type":
            given_type = text[len(name):].strip()
            valid_types = [
                t for t in USER_FRIENDLY_TYPES
                if USER_FRIENDLY_TYPES[t] not in UNHANDLED_TYPES
            ]
            if given_type not in valid_types:
                error = "Valid types: " + ", ".join(valid_types)
                browser.set_status_error(error)
                return
            item_type = USER_FRIENDLY_TYPES[given_type]
            self.set_item_type(browser, item_type)

    def set_item_type(self, browser: Browser, item_type: ItemType):
        """Re-parse the current page using this item type."""
        if browser.current_scheme != self.scheme or not browser.current_page:
            browser.set_status_error("Can only set item types on Gopher URLs.")
            return

        logging.debug(f"Force parsing current page as {item_type}…")
        current_source = browser.current_page.source
        new_page = get_page_from_source(current_source, item_type)
        browser.load_page(new_page)

        # If possible, set the correct item type in the URL path as well.
        url = browser.current_url
        parts = parse_url(browser.current_url)
        type_path_match = TYPE_PATH_RE.match(parts["path"])
        if type_path_match:
            path = type_path_match.group(2)
            parts["path"] = f"/{item_type.value}{path}"
            browser.current_url = unparse_url(parts)


def request(host: str, port: int, path: str, timeout: int) -> bytes:
    """Send a Gopher request and return the received bytes."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        raise GopherPluginException("failed to establish connection")

    try:
        request_str = path.encode() + b"\r\n"
    except ValueError as exc:
        raise GopherPluginException("could not encode path")

    sock.sendall(request_str)
    response = b""
    while True:
        try:
            buf = sock.recv(4096)
        except socket.timeout:
            buf = None
        if not buf:
            return response
        response += buf
    return decoded


def parse_response(response: bytes, item_type: ItemType, encoding: str ="utf8"):
    """Parse a Gopher response."""
    decoded = response.decode(encoding=encoding, errors="replace")
    return get_page_from_source(decoded, item_type)


def get_page_from_source(source: str, item_type: ItemType):
    """Get a Page object from a decoded source text."""
    metalines, links = parse_source(source, item_type)
    return Page(source, metalines, links)


def parse_source(source: str, item_type: ItemType):
    """Generate metalines and a Links instance for this source text.

    The item_type must be a type that can be parsed: FILE or DIR. Any other
    item type will silently result in no metalines.
    """
    metalines = []
    links = Links()

    if item_type == ItemType.FILE:
        for line in source.split("\n"):
            line = line.rstrip("\r")
            metalines.append(({"type": LineType.PARAGRAPH}, line))

    # Gopher maps are kind of the default here, so it should be quite safe to
    # parse any kind of text data.
    elif item_type == ItemType.DIR:
        current_link_id = 1
        # Split lines on \n and discard \r separately because some maps do not
        # end lines with \r\n all the time.
        for line in source.split("\n"):
            line = line.rstrip("\r")
            ltype, tline = line[:1], line[1:]
            if ltype == "." and not tline:
                break

            parts = tline.split("\t")
            # If the map is poorly formatted and parts are missing, pad with
            # empty parts.
            while len(parts) < 4:
                parts.append("")

            item_type = ItemType(ltype)
            label, path, host, port = parts

            # INFO: render as a simple text line.
            if item_type == ItemType.INFO:
                metalines.append(({"type": LineType.PARAGRAPH}, label))
                continue

            # ERROR: render as an error line.
            if item_type == ItemType.ERROR:
                metalines.append(({"type": LineType.ERROR}, label))
                continue

            # Other item types are rendered as links, with a special case for
            # "URL:"-type selectors in HTML items.
            if item_type == ItemType.HTML and path[:4].upper() == "URL:":
                link_url = path[4:]
            else:
                link_url = f"gopher://{host}:{port}/{ltype}{path}"

            meta = {
                "type": LineType.LINK,
                "url": link_url,
                "link": current_link_id
            }
            links[current_link_id] = link_url

            icon = ICONS.get(item_type) or f"({ltype})"
            text = f"[{current_link_id}] {icon} {label}"
            metalines.append((meta, text))
            current_link_id += 1

    return metalines, links


plugin = GopherPlugin()
