"""TOFU implementation.

As of writing there is still some debate around it, so it is quite messy and
requires more clarity both in specification and in our own implementation.
"""

import hashlib
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from bebop.fs import get_user_data_path


STASH_LINE_RE = re.compile(r"(\S+) (\S+) (\S+)")

WRONG_FP_ALERT = """\
The request could not complete because the certificate presented by the server \
does not match the certificate stored in the local stash.

``` details of the fingerprint mismatch
Hostname:           {hostname}
Local fingerprint:  {local_fp}
Server fingerprint: {remote_fp}
```

If you are sure this new certificate can be trusted, press ":" and type the \
following command to remove the previous certificate from the local stash, \
then retry your request:

``` command to use to forget about the previous certificate
forget-certificate {hostname}
```

You can also manually remove the certificate line from the known hosts file in \
your user data directory.

## FAQ

### What is this mismatch about?

Gemini uses TOFU (Trust On First Use) to verify the identity of the server you \
are visiting. It means that the first time you visited this capsule, it showed \
you its unique ID, but this time the ID is different, so the trust is broken.

Capsule owners often tell in advance when they are about the use a new \
certificate, but they may have forgotten or you may have missed it. Maybe the \
old certificate expired and/or has been replaced for another reason (e.g. \
using a far away expiration time, borking certificates during a migration, …)

### Am I being hacked?

Probably not, but if you are visiting a sensitive capsule, make sure you're \
confident enough before trusting this new certificate.

### How to ensure this new certificate can be trusted?

Can you join the owner through mail or instant messaging? This is the simplest \
way for you to make sure that the server is fine, and maybe alert the server \
owner that there might be an issue.
"""


def get_cert_stash_path() -> Path:
    """Return the default certificate stash path."""
    return get_user_data_path() / "known_hosts.txt"


def load_cert_stash(stash_path: Path) -> Optional[Dict]:
    """Return the certificate stash from the file, or None on error.

    The stash is a dict with host names as keys and tuples as values. Tuples
    have four elements:
    - the fingerprint algorithm (only SHA-512 is supported),
    - the fingerprint as an hexstring,
    - the timestamp of the expiration date,
    - a boolean that is True when the stash is loaded from a file, i.e. always
      true for entries loaded in this function, but should be false when it
      concerns a certificate temporary trusted for the session only; this flag
      is used to decide whether to save the certificate in the stash at exit.
    """
    stash = {}
    try:
        with open(stash_path, "rt") as stash_file:
            for line in stash_file:
                match = STASH_LINE_RE.match(line)
                if not match:
                    continue
                name, algo, fingerprint = match.groups()
                stash[name] = (algo, fingerprint, True)
    except (OSError, ValueError):
        return None
    return stash


def save_cert_stash(stash: dict, stash_path: Path):
    """Save the certificate stash."""
    try:
        with open(stash_path, "wt") as stash_file:
            for name, entry in stash.items():
                algo, fingerprint, is_permanent = entry
                if not is_permanent:
                    continue
                entry_line = f"{name} {algo} {fingerprint}\n"
                stash_file.write(entry_line)
    except (OSError, ValueError) as exc:
        logging.error(f"Failed to save certificate stash '{stash_path}': {exc}")


class CertStatus(Enum):
    """Value returned by validate_cert."""
    # Cert is valid: proceed.
    VALID = 0      # Known and valid.
    VALID_NEW = 1  # New and valid.
    # Cert is unusable or wrong: abort.
    ERROR = 2              # General error.
    WRONG_FINGERPRINT = 3  # Fingerprint in the stash is different.


def validate_cert(der, hostname, cert_stash) -> Dict[str, Any]:
    """Return a dict containing validation info for this certificate.

    Returns:
    The validation dict can contain two keys:
    - status: CertStatus, always present.
    - hash: DER hash to be used as certificate fingerprint, present if status is
      not CertStatus.ERROR.
    - saved_hash: fingerprint for this hostname in the local stash, present if
      status is CertStatus.WRONG_FINGERPRINT.
    """
    if der is None:
        return {"status": CertStatus.ERROR}
    
    known = False

    # Check the entire certificate fingerprint.
    cert_hash = hashlib.sha512(der).hexdigest()
    result = {"hash": cert_hash}  # type: Dict[str, Any]
    if hostname in cert_stash:
        _, fingerprint, _ = cert_stash[hostname]
        if cert_hash != fingerprint:
            result.update(
                status=CertStatus.WRONG_FINGERPRINT,
                saved_hash=fingerprint
            )
            return result
        known = True

    result.update(status=CertStatus.VALID if known else CertStatus.VALID_NEW)
    return result


def trust_fingerprint(stash, hostname, algo, fingerprint, trust_always=False):
    """Add a fingerprint entry to this stash."""
    stash[hostname] = (algo, fingerprint, trust_always)


def untrust_fingerprint(stash, hostname):
    """Remove a fingerprint entry from this stash; return True on deletion."""
    if hostname in stash:
        del stash[hostname]
        return True
    return False
