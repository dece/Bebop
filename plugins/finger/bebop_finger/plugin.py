import subprocess
from typing import Optional

from bebop.browser.browser import Browser
from bebop.navigation import parse_url
from bebop.page import Page
from bebop.plugins import SchemePlugin


class FingerPlugin(SchemePlugin):

    def __init__(self) -> None:
        super().__init__("finger")

    def open_url(self, browser: Browser, url: str) -> Optional[str]:
        parts = parse_url(url, default_scheme="finger")
        host = parts["netloc"]
        user = parts["path"][1:]  # Strip leading '/' from path.
        if not host:
            browser.set_status_error(f"Could not parse {url}.")
            return None

        raw_output = self.request(browser, host, user)
        if raw_output is None:
            return None

        try:
            output = raw_output.decode(errors="replace")
        except ValueError:
            browser.set_status_error("Failed to decode finger output.")
            return None

        browser.load_page(Page.from_text(output))
        browser.current_url = url
        return url

    def request(self, browser: Browser, host: str, user: str):
        target = f"{user}@{host}"
        browser.set_status(f"Requesting {target}…")
        command = ["finger", target]
        try:
            output = subprocess.check_output(command, stderr=subprocess.PIPE)
        except FileNotFoundError:
            browser.set_status_error("Finger program not found.")
        except subprocess.CalledProcessError as exc:
            finger_error = exc.stderr.decode(errors="replace").replace("\n", "")
            error = f"Finger failed with code {exc.returncode}: {finger_error}"
            browser.set_status_error(error)
        else:
            return output


plugin = FingerPlugin()
