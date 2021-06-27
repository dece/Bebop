"""Gemini-related features of the browser."""

import logging
from typing import Optional

from bebop.browser.browser import Browser
from bebop.command_line import CommandLine
from bebop.downloads import get_download_path
from bebop.fs import get_identities_list_path
from bebop.identity import (
    ClientCertificateException, create_certificate, get_cert_and_key,
    get_identities_for_url, load_identities, save_identities
)
from bebop.navigation import set_parameter
from bebop.page import Page, get_render_options
from bebop.preferences import get_url_render_mode_pref
from bebop.protocol import Request, Response
from bebop.tofu import trust_fingerprint, untrust_fingerprint, WRONG_FP_ALERT


MAX_URL_LEN = 1024


def open_gemini_url(
    browser: Browser,
    url: str,
    redirects: int =0,
    use_cache: bool =False,
    cert_and_key=None
) -> Optional[str]:
    """Open a Gemini URL and set the formatted response as content.

    While the specification is not set in stone, every client takes a slightly
    different approach to enforcing TOFU. Read the `Request.connect` docs to
    find about cases where connection is aborted without asking the user. What
    interests us here is what happens when the user should decide herself? This
    happens in several cases, matching the request possible states. Here is
    what Bebop do (or want to do):

    - STATE_INVALID_CERT: the certificate has non-fatal issues; we may
      present the user the problems found and let her decide whether to trust
      temporarily the certificate or not BUT we currently do not parse the
      certificate's fields, not even the pubkey, so this state is never used.
    - STATE_UNKNOWN_CERT: the certificate is valid but has not been seen before;
      as we're doing TOFU here, we could automatically trust it or let the user
      choose. For simplicity, we always trust it permanently.

    Arguments:
    - browser: Browser object making the request.
    - url: a valid URL with Gemini scheme to open.
    - redirects: current amount of redirections done to open the initial URL.
    - use_cache: if true, look up if the page is cached before requesting it.
    - cert_and_key: if not None, a tuple of paths to a client cert/key to use.

    Returns:
    The final successfully handled URL on success, None otherwise. Redirected
    URLs are not returned.
    """
    if len(url) >= MAX_URL_LEN:
        browser.set_status_error("Request URL too long.")
        return None

    loading_message_verb = "Loading" if redirects == 0 else "Redirecting to"
    loading_message = f"{loading_message_verb} {url}…"
    browser.set_status(loading_message)

    # If this URL used to request an identity, provide it.
    if not cert_and_key:
        url_identities = get_identities_for_url(browser.identities, url)
        identity = select_identity(url_identities)
        if identity:
            cert_and_key = get_cert_and_key(identity["id"])

    if use_cache and url in browser.cache:
        browser.load_page(browser.cache[url])
        browser.current_url = url
        return url

    logging.info(
        f"Request {url}"
        + (f" using cert and key {cert_and_key}" if cert_and_key else "")
    )
    req = Request(url, browser.stash, identity=cert_and_key)
    connect_timeout = browser.config["connect_timeout"]
    connected = req.connect(connect_timeout)
    if not connected:
        if req.state == Request.STATE_ERROR_CERT:
            error = f"Certificate was missing or corrupt ({url})."
        elif req.state == Request.STATE_UNTRUSTED_CERT:
            _handle_untrusted_cert(browser, req)
            error = f"Certificate has been changed ({url})."
        elif req.state == Request.STATE_CONNECTION_FAILED:
            error_details = ": " + req.error if req.error else "."
            error = f"Connection failed ({url})" + error_details
        else:
            error = f"Connection failed ({url})."
        browser.set_status_error(error)
        return None

    if req.state == Request.STATE_INVALID_CERT:
        pass
    elif req.state == Request.STATE_UNKNOWN_CERT:
        # Certificate is valid but unknown: trust it permanently.
        hostname = req.hostname
        fingerprint = req.cert_validation["hash"]
        trust_fingerprint(
            browser.stash,
            hostname,
            "SHA-512",
            fingerprint,
            trust_always=True
        )

    data = req.proceed()
    if not data:
        browser.set_status_error(f"Server did not respond in time ({url}).")
        return None
    response = Response.parse(data)
    if not response:
        browser.set_status_error(f"Server response parsing failed ({url}).")
        return None

    return _handle_response(browser, response, url, redirects)


def _handle_untrusted_cert(browser: Browser, request: Request):
    """Handle a mismatch between known & server fingerprints.

    This function formats an alert page to explain to the user what the hell is
    going on and displays it.
    """
    remote_fp = request.cert_validation["hash"]
    local_fp = request.cert_validation["saved_hash"]
    alert_page_source = WRONG_FP_ALERT.format(
        hostname=request.hostname,
        local_fp=local_fp,
        remote_fp=remote_fp,
    )
    alert_page = Page.from_gemtext(
        alert_page_source,
        get_render_options(browser.config)
    )
    browser.load_page(alert_page)


def _handle_response(
    browser: Browser,
    response: Response,
    url: str,
    redirects: int
) -> Optional[str]:
    """Handle a response from a Gemini server.

    Returns:
    The final URL on success, None otherwise.
    """
    logging.info(f"Response {response.code} {response.meta}")
    if response.code == 20:
        return _handle_successful_response(browser, response, url)
    elif response.generic_code == 30 and response.meta:
        # On redirections, we go back to open_url as the redirection may be to
        # another protocol. Discard the result of this request.
        browser.open_url(
            response.meta,
            base_url=url,
            redirects=redirects + 1
        )
    elif response.generic_code in (40, 50):
        error = f"Server error: {response.meta or Response.code.name}"
        browser.set_status_error(error)
    elif response.generic_code == 10:
        return _handle_input_request(browser, url, response.meta)
    elif response.code == 60:
        return _handle_cert_required(browser, response, url, redirects)
    elif response.code in (61, 62):
        details = response.meta or Response.code.name
        error = f"Client certificate error: {details}"
        browser.set_status_error(error)
    else:
        error = f"Unhandled response code {response.code}"
        browser.set_status_error(error)
    return None


def _handle_successful_response(browser: Browser, response: Response, url: str):
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

    Returns:
    The successfully handled URL on success, None otherwise.
    """
    # Use appropriate response parser according to the MIME type.
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
                render_opts = get_render_options(browser.config)
                pref_mode = get_url_render_mode_pref(browser.capsule_prefs, url)
                if pref_mode:
                    render_opts.mode = pref_mode
                page = Page.from_gemtext(text, render_opts)
        else:
            encoding = "utf-8"
            text = response.content.decode(encoding, errors="replace")
            page = Page.from_text(text)
        if page:
            page.mime = mime_type
            page.encoding = encoding
    else:
        download_dir = browser.config["download_path"]
        filepath = get_download_path(url, download_dir=download_dir)

    # If a page has been produced, load it. Else if a file has been retrieved,
    # download it.
    if page:
        browser.load_page(page)
        browser.current_url = url
        browser.cache[url] = page
        return url
    elif filepath:
        try:
            with open(filepath, "wb") as download_file:
                download_file.write(response.content)
        except OSError as exc:
            browser.set_status_error(f"Failed to save {url} ({exc})")
        else:
            browser.set_status(f"Downloaded {url} ({mime_type.short}).")
            browser.last_download = mime_type, filepath
            return url
    elif error:
        browser.set_status_error(error)
    return None


def _handle_input_request(
    browser: Browser,
    from_url: str,
    message: str =None
) -> Optional[str]:
    """Focus command-line to pass input to the server.

    Returns:
    The result of `open_gemini_url` with the new request including user input.
    """
    if message:
        browser.set_status(f"Input needed: {message}")
    else:
        browser.set_status("Input needed:")
    user_input = browser.command_line.focus(CommandLine.CHAR_TEXT)
    if not user_input:
        return
    url = set_parameter(from_url, user_input)
    return open_gemini_url(browser, url)


def _handle_cert_required(
    browser: Browser,
    response: Response,
    url: str,
    redirects: int
) -> Optional[str]:
    """Find a matching identity and resend the request with it.

    Returns:
    The result of `open_gemini_url` with the client certificate provided.
    """
    identities = load_identities(get_identities_list_path())
    if identities is None:
        browser.set_status_error("Can't load identities.")
        return None
    browser.identities = identities

    url_identities = get_identities_for_url(browser.identities, url)
    if not url_identities:
        identity = create_identity(browser, url, reason=response.meta)
        if not identity:
            return None
        browser.identities[url] = [identity]
        save_identities(browser.identities, get_identities_list_path())
    else:
        identity = select_identity(url_identities)

    cert_path, key_path = get_cert_and_key(identity["id"])
    return open_gemini_url(
        browser,
        url,
        redirects=redirects + 1,
        cert_and_key=(cert_path, key_path)
    )


def select_identity(identities: list):
    """Let user select the appropriate identity among candidates."""
    # TODO support multiple identities; for now we just use the first available.
    return identities[0] if identities else None


def create_identity(browser: Browser, url: str, reason: Optional[str] =None):
    """Walk the user through identity creation.

    Returns:
    The created identity on success (already registered in identities
    """
    prompt_text = "Create client certificate?"
    if reason:
        prompt_text += f" Reason: {reason}"
    key = browser.prompt(prompt_text)
    if key != "y":
        browser.reset_status()
        return None

    common_name = browser.get_user_text_input(
        "Name? The server may use it as your username.",
        CommandLine.CHAR_TEXT,
        strip=True,
        escape_to_none=True
    )
    if common_name is None:
        browser.reset_status()
        return None

    browser.set_status("Generating certificate…")
    gen_command = browser.config["generate_client_cert_command"]
    try:
        mangled_name = create_certificate(url, common_name, gen_command)
    except ClientCertificateException as exc:
        browser.set_status_error(exc.message)
        return None

    browser.reset_status()
    return {"name": common_name, "id": mangled_name}


def forget_certificate(browser: Browser, hostname: str):
    """Remove the fingerprint associated to this hostname for the cert stash."""
    key = browser.prompt(f"Remove fingerprint for {hostname}?")
    if key != "y":
        browser.reset_status()
        return
    if untrust_fingerprint(browser.stash, hostname):
        browser.set_status(f"Known certificate for {hostname} removed.")
    else:
        browser.set_status_error(f"Known certificate for {hostname} not found.")
