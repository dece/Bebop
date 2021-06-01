"""Identity management, i.e. client certificates.

Identities are created when a server requests them for the first time, and saved
with the corresponding URL. The certificate is automatically presented when the
URL is revisited, and all "children" URLs.

Identities are stored on disk as pairs of certificates/keys. URLs are stored in
an identity file, `identities.json`, a simple URL dict that can be looked up for
identities to use, mapped to an ID to identify the cert/key files.

The identity file and the identities dict both have the following format:

``` json
{
    "gemini://example.com/app": [
        {
            "name": "test",
            "id": "geminiexamplecomapp-test",
        }
    ]
}
```
"""

import hashlib
import json
import logging
import secrets
import subprocess
from pathlib import Path
from typing import Optional

from bebop.fs import get_identities_path


def load_identities(identities_path: Path) -> Optional[dict]:
    """Return saved identities or None on error."""
    identities = {}
    try:
        with open(identities_path, "rt") as identities_file:
            identities = json.load(identities_file)
    except (OSError, ValueError) as exc:
        logging.error(f"Failed to load identities '{identities_path}': {exc}")
        return None
    return identities


def save_identities(identities: dict, identities_path: Path):
    """Save the certificate stash. Return True on success."""
    try:
        with open(identities_path, "wt") as identities_file:
            json.dump(identities, identities_file, indent=2)
    except (OSError, ValueError) as exc:
        logging.error(f"Failed to save identities '{identities_path}': {exc}")
        return False
    return True


class ClientCertificateException(Exception):

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message


def get_identities_for_url(identities: dict, url: str) -> list:
    """For a given URL, return all its identities.

    If several URLs are prefixes of the given URL, e.g. we look up
    "gemini://host/app/sub" and there are identities for both
    "gemini://host/app" and "gemini://host/app/sub", the longest URL's
    identities are returned (here the latter).
    """
    candidates = [key for key in identities if url.startswith(key)]
    if not candidates:
        return []
    return identities[max(candidates, key=len)]


def get_cert_and_key(cert_id: str):
    """Return the paths of the certificate and key file for this ID."""
    directory = get_identities_path()
    return directory / f"{cert_id}.crt", directory / f"{cert_id}.key"


def create_certificate(url: str, common_name: str, gen_command: list):
    """Create a secure self-signed certificate using system's OpenSSL."""
    identities_path = get_identities_path()
    mangled_name = get_mangled_name(url, common_name)
    cert_path = identities_path / f"{mangled_name}.crt"
    key_path = identities_path / f"{mangled_name}.key"

    command = []
    for part in gen_command:
        if "{key_path}" in part:
            part = part.format(key_path=str(key_path))
        if "{cert_path}" in part:
            part = part.format(cert_path=str(cert_path))
        if "{common_name}" in part:
            part = part.format(common_name=common_name)
        command.append(part)

    try:
        subprocess.check_call(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        error = "Could not create certificate: " + str(exc)
        raise ClientCertificateException(error)

    cert_path.chmod(0o644)
    key_path.chmod(0o600)
    return mangled_name


def get_mangled_name(url: str, common_name: str) -> str:
    """Return a mangled name for the certificate and key files.

    This is not obfuscation at all. The mangling is extremely simple and is
    just a way to produce names easier on the file system than full URLs.

    The mangling is:
    `sha256(md5(url) + "-" + common_name + "-" + 8_random_hex_digits)`
    with characters that can't be UTF-8 encoded replaced by U+FFFD REPLACEMENT
    CHARACTER.
    """
    encoded_url = hashlib.md5(url.encode(errors="replace")).hexdigest()
    random_hex = hex(secrets.randbits(32))[2:].zfill(8)
    name = f"{encoded_url}-{common_name}-{random_hex}"
    return hashlib.sha256(name.encode(errors="replace")).hexdigest()
