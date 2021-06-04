"""Gemini protocol implementation."""

import logging
import re
import socket
import ssl
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from bebop.mime import DEFAULT_MIME_TYPE, MimeType
from bebop.navigation import parse_host_and_port
from bebop.tofu import CertStatus, validate_cert


GEMINI_URL_RE = re.compile(r"gemini://(?P<host>[^/]+)(?P<path>.*)")
LINE_TERM = b"\r\n"


class Request:
    """A Gemini request.

    Details about the request itself can be found in the Gemini specification.
    This class allows you to do a request in 2 times: first opening the
    TLS connection to apply security checks, then aborting or proceeding by
    sending the request header and receiving the response:

    1. Instantiate a Request.
    2. `connect` opens the connection and aborts it or leaves the caller free to
       check stuff.
    3. `proceed` or `abort` can be called.

    Attributes:
    - url: URL to open.
    - cert_stash: certificate stash to use an possibly update.
    - state: request state.
    - hostname: hostname derived from url, stored when `connect` is called.
    - payload: bytes object of the payload request; build during `connect`, used
      during `proceed`.
    - ssock: TLS-wrapped socket.
    - cert_validation: validation results dict, set after certificate has been
      reviewed.
    - error: human-readable connection error, may be set during `connect`.
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

    def __init__(self, url, cert_stash, identity=None):
        self.url = url
        self.cert_stash = cert_stash
        self.state = Request.STATE_INIT
        self.hostname = ""
        self.payload = b""
        self.ssock = None
        self.cert_validation = None
        self.error = ""
        self.identity = identity

    def connect(self, timeout: int) -> bool:
        """Connect to a Gemini server and return a RequestEventType.

        Return True if the connection is established. The caller has to verify
        the request state and propose appropriate choices to the user if the
        certificate status is not CertStatus.VALID (Request.STATE_OK).

        If connect returns False, the secure socket is aborted before return so
        there is no need to call `abort`. If connect returns True, it is up to the
        caller to decide whether to continue (call `proceed`) the connection or
        abort it (call `abort`).

        The request `state` is updated to reflect the connection state after the
        function returns. The following list describes states related to
        connection failure (False returned):

        - STATE_INVALID_URL: URL is not valid.
        - STATE_CONNECTION_FAILED: connection failed, either TCP timeout or
          local TLS failure. Additionally, the request `error` attribute is set
          to an error string describing the issue.

        For all request states from now on, the `cert_validation` attribute is
        updated with the result of the certificate validation.

        The following list describes states related to validation failure (False
        returned):

        - STATE_ERROR_CERT: server certificate could not be validated at all.
        - STATE_UNTRUSTED_CERT: server certificate mismatched the known
          certificate for that hostname. The user should be presented with
          options to solve the matter.

        For other states, the connection is not aborted (True returned):

        - STATE_INVALID_CERT: the certificate has one or more issues, e.g.
          mismatching hostname or it is expired.
        - STATE_UNKNOWN_CERT: the certificate is valid but unknown.
        - STATE_OK: the certificate is valid and matches the known certificate
          of that hostname.

        After this function returns, the request state cannot be STATE_INIT.

        Additional notes:

        - The DER hash is compared against the fingerprint for this hostname
          *and port*; the specification does not tell much about that, but we
          are slightly more restrictive here by adding the port in the equation.
        - The state STATE_INVALID_CERT is actually never used in Bebop because
          of the current tendency to ignore any certificate fields and only
          check the whole cert fingerprint. Here it is considered the same as a
          valid certificate.
        """
        # Get hostname and port from the URL.
        url_parts = GEMINI_URL_RE.match(self.url)
        if not url_parts:
            self.state = Request.STATE_INVALID_URL
            return False

        host = url_parts.groupdict()["host"]
        host_and_port = parse_host_and_port(host, 1965)
        if host_and_port is None:
            self.state = Request.STATE_INVALID_URL
            return False
        hostname, port = host_and_port
        self.hostname = hostname

        # Prepare the Gemini request.
        try:
            self.payload = self.url.encode()
        except ValueError:
            self.state = Request.STATE_INVALID_URL
            return False
        self.payload += LINE_TERM

        # Connect to the server.
        try:
            sock = socket.create_connection((hostname, port), timeout=timeout)
        except OSError as exc:
            self.state = Request.STATE_CONNECTION_FAILED
            self.error = exc.strerror
            return False

        # Setup TLS.
        context = Request.get_ssl_context()
        if self.identity:
            try:
                context.load_cert_chain(*self.identity)
            except FileNotFoundError as exc:
                sock.close()
                self.state = Request.STATE_CONNECTION_FAILED
                self.error = f"Could not load identity files ({exc})"
                logging.error(f"Failed to load identity files {self.identity}")
                return False

        try:
            self.ssock = context.wrap_socket(sock, server_hostname=hostname)
        except OSError as exc:
            sock.close()
            self.state = Request.STATE_CONNECTION_FAILED
            self.error = exc.strerror
            return False

        # Validate server certificate.
        der = self.ssock.getpeercert(binary_form=True)
        self.cert_validation = validate_cert(der, hostname, self.cert_stash)
        cert_status = self.cert_validation["status"]
        if cert_status == CertStatus.ERROR:
            self.abort()
            self.state = Request.STATE_ERROR_CERT
            return False
        if cert_status == CertStatus.WRONG_FINGERPRINT:
            self.abort()
            self.state = Request.STATE_UNTRUSTED_CERT
            return False

        if cert_status == CertStatus.VALID_NEW:
            self.state = Request.STATE_UNKNOWN_CERT
        else:  # self.cert_status in (VALID, VALID_NEW, INVALID_CERT)
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
    """A Gemini response.

    Response objects can be created only by parsing a Gemini response using the
    static `parse` method, so you're guaranteed to have a valid object.

    Attributes:
    - code: the status code returned by the server.
    - meta: optional meta content.
    - content: bytes as returned by the server, only in successful requests.
    """

    code: StatusCode
    meta: str = ""
    content: bytes = b""

    HEADER_RE = re.compile(r"(\d{2}) (.*)")
    MAX_META_LEN = 1024

    @property
    def generic_code(self) -> int:
        """See `Response.get_generic_code`."""
        return Response.get_generic_code(self.code)

    def get_mime_type(self) -> MimeType:
        """Return the MIME type if possible, else the default MIME type."""
        return MimeType.from_str(self.meta) or DEFAULT_MIME_TYPE

    @staticmethod
    def parse(data: bytes) -> Optional["Response"]:
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
    def get_generic_code(code: int) -> int:
        """Return the generic version (x0) of this code."""
        return code - (code % 10)
