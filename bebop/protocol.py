"""Gemini protocol implementation."""

import re
import socket
import ssl
from dataclasses import dataclass
from enum import IntEnum

from bebop.tofu import CertStatus, CERT_STATUS_INVALID, validate_cert


GEMINI_URL_RE = re.compile(r"gemini://(?P<host>[^/]+)(?P<path>.*)")
LINE_TERM = b"\r\n"


def parse_gemini_url(url):
    """Return a dict containing the hostname and the request path, or None."""
    match = GEMINI_URL_RE.match(url)
    return match.groupdict() if match else None


class Request:
    """A Gemini request.

    Details about the request itself can be found in the Gemini specification.
    This class allows you to do a request in 2 times: first opening the
    TLS connection to apply security checks, then aborting or proceeding by
    sending the request header and receiving the response:

    1. Instantiate a Request.
    2. `connect` opens the connection, leaves the caller free to check stuff.
    3. `proceed` or `abort` can be called.
    """

    # Initial state, connection is not established yet.
    STATE_INIT = 0
    # An error has occured during cert verification, connection is aborted.
    STATE_ERROR_CERT = 1
    # An invalid URL has been provided, connection is aborted.
    STATE_INVALID_URL = 2
    # Invalid cert: user should abort or temporarily trust the cert.
    STATE_INVALID_CERT = 3
    # Unknown cert: user should abort, temporarily or always trust the cert.
    STATE_UNKNOWN_CERT = 4
    # Untrusted cert: connection is aborted, manually edit the stash.
    STATE_UNTRUSTED_CERT = 5
    # Valid and trusted cert: proceed.
    STATE_OK = 6
    # Connection failed.
    STATE_CONNECTION_FAILED = 7

    def __init__(self, url, cert_stash):
        self.url = url
        self.cert_stash = cert_stash
        self.state = Request.STATE_INIT
        self.payload = b""
        self.ssock = None
        self.cert = None
        self.cert_status = None
        self.error = ""

    def connect(self):
        """Connect to a Gemini server and return a RequestEventType.

        Return True if the connection is established. The caller has to verify
        the request state and propose appropriate choices to the user if the
        certificate status is not CertStatus.VALID (Request.STATE_OK).

        If connect returns False, the secure socket is aborted before return. If
        connect returns True, it is up to the caller to decide whether to
        continue (call proceed) the connection or abort it (call abort).
        """
        url_parts = parse_gemini_url(self.url)
        if not url_parts:
            self.state = Request.STATE_INVALID_URL
            return False
        hostname = url_parts["host"]
        if ":" in hostname:
            hostname, port = hostname.split(":", maxsplit=1)
            try:
                port = int(port)
            except ValueError:
                self.state = Request.STATE_INVALID_URL
                return False
        else:
            port = 1965

        try:
            self.payload = self.url.encode()
        except ValueError:
            self.state = Request.STATE_INVALID_URL
            return False
        self.payload += LINE_TERM

        try:
            sock = socket.create_connection((hostname, port), timeout=10)
        except OSError as exc:
            self.state = Request.STATE_CONNECTION_FAILED
            self.error = exc.strerror
            return False

        context = Request.get_ssl_context()
        try:
            self.ssock = context.wrap_socket(sock, server_hostname=hostname)
        except OSError as exc:
            self.state = Request.STATE_CONNECTION_FAILED
            self.error = exc.strerror
            return False

        der = self.ssock.getpeercert(binary_form=True)
        self.cert_status, self.cert = \
            validate_cert(der, hostname, self.cert_stash)
        if self.cert_status == CertStatus.ERROR:
            self.abort()
            self.state = Request.STATE_ERROR_CERT
            return False
        if self.cert_status == CertStatus.WRONG_FINGERPRINT:
            self.abort()
            self.state = Request.STATE_UNTRUSTED_CERT
            return False

        if self.cert_status in CERT_STATUS_INVALID:
            self.state = Request.STATE_INVALID_CERT
        elif self.cert_status == CertStatus.VALID_NEW:
            self.state = Request.STATE_UNKNOWN_CERT
        else:  # self.cert_status == CertStatus.VALID
            self.state = Request.STATE_OK
        return True

    def abort(self):
        """Close the connection."""
        self.ssock.close()

    def proceed(self):
        """Complete the request: send the payload and return received data."""
        self.ssock.sendall(self.payload)
        response = b""
        while True:
            try:
                buf = self.ssock.recv(4096)
            except socket.timeout:
                buf = None
            if not buf:
                return response
            response += buf

    @staticmethod
    def get_ssl_context():
        """Return a secure SSL context that is adequate for Gemini."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context


class StatusCode(IntEnum):
    UNKNOWN = 0
    INPUT = 10
    SENSITIVE_INPUT = 11
    SUCCESS = 20
    REDIRECT = 30
    PERMANENT_REDIRECT = 31
    TEMP_FAILURE = 40
    SERVER_UNAVAILABLE = 41
    CGI_ERROR = 42
    PROXY_ERROR = 43
    SLOW_DOWN = 44
    PERM_FAILURE = 50
    NOT_FOUND = 51
    GONE = 52
    PROXY_REQUEST_REFUSED = 53
    BAD_REQUEST = 59
    CERT_REQUIRED = 60
    CERT_NOT_AUTHORISED = 61
    CERT_NOT_VALID = 62
    _missing_ = lambda _: StatusCode.UNKNOWN


@dataclass
class Response:
    """A Gemini response."""

    code: StatusCode
    meta: str = ""
    content: bytes = b""

    HEADER_RE = re.compile(r"(\d{2}) (.*)")
    MAX_META_LEN = 1024

    @property
    def generic_code(self):
        return Response.get_generic_code(self.code)

    @staticmethod
    def parse(data):
        """Parse a received response."""
        try:
            response_header_len = data.index(LINE_TERM)
            response_header = data[:response_header_len].decode()
        except ValueError:
            return None
        match = Response.HEADER_RE.match(response_header)
        if not match:
            return None
        code, meta = match.groups()
        if len(meta) > Response.MAX_META_LEN:
            return None
        response = Response(StatusCode(int(code)), meta=meta)
        if response.generic_code == StatusCode.SUCCESS:
            content_offset = response_header_len + len(LINE_TERM)
            response.content = data[content_offset:]
        elif response.code == StatusCode.UNKNOWN:
            return None
        return response

    @staticmethod
    def get_generic_code(code):
        """Return the generic version (x0) of this code."""
        return code - (code % 10)
