import logging
import re
import socket
from enum import Enum
from typing import Optional

from bebop.browser.browser import Browser
from bebop.links import Links
from bebop.metalines import LineType
from bebop.navigation import parse_url, parse_host_and_port
from bebop.page import Page
from bebop.plugins import SchemePlugin


class ItemType(Enum):
    FILE = "0"
    DIR = "1"
    CSO = "2"
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


ICONS = {
    ItemType.FILE: "📄",
    ItemType.DIR: "📂",
    ItemType.ERROR: "❌",
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

    def open_url(self, browser: Browser, url: str) -> Optional[str]:
        parts = parse_url(url)
        host = parts["netloc"]
        host_and_port = parse_host_and_port(host, 70)
        if host_and_port is None:
            browser.set_status_error("Could not parse gopher URL.")
            return None
        host, port = host_and_port
        path = parts["path"]

        # If the URL has an item type, use it to properly parse the response.
        type_path_match = TYPE_PATH_RE.match(path)
        if type_path_match:
            item_type = ItemType(type_path_match.group(1))
            path = type_path_match.group(2)
            logging.debug(f"Gopher type for URL: type {item_type} path {path}")
        else:
            # Else you're on your own! If we're opening a link of a map, find
            # that item type. Default to DIR item type.
            item_type = ItemType.DIR
            if browser.current_page:
                for meta, line in browser.current_page.metalines:
                    if meta.get("url") == url:
                        item_type = meta.get("gophertype") or ItemType.DIR
                        break
            logging.debug(f"Gopher type from current map: type {item_type}")

        browser.set_status(f"Loading {url}…")
        timeout = browser.config["connect_timeout"]
        try:
            response = self.request(host, port, path, timeout)
            page = parse_response(response, item_type)
        except GopherPluginException as exc:
            browser.set_status_error("Error: " + exc.message)
            return None
        browser.load_page(page)
        browser.current_url = url
        return url

    def request(self, host: str, port: int, path: str, timeout: int):
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
    decoded = response.decode(encoding=encoding, errors="replace")
    metalines, links = parse_source(decoded, item_type)
    return Page(decoded, metalines, links)


def parse_source(source: str, item_type: ItemType):
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
        for line in source.split("\r\n"):
            ltype, tline = line[:1], line[1:]
            if ltype == "." and not tline:
                break

            parts = tline.split("\t")
            if len(parts) != 4:
                # TODO move me away
                # Does not seem to be split by tabs, may be a file.
                metalines.append(({"type": LineType.PARAGRAPH}, line))
                continue

            item_type = ItemType(ltype)
            label, path, host, port = parts
            if item_type == ItemType.INFO:
                meta = {"type": LineType.PARAGRAPH}
                metalines.append((meta, label))
                continue

            if item_type == ItemType.HTML and path[:4].upper() == "URL:":
                link_url = path[4:]
            else:
                link_url = f"gopher://{host}:{port}/{ltype}{path}"

            meta = {
                "type": LineType.LINK,
                "gophertype": item_type,
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
