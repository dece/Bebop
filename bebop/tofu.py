"""TOFU implementation.

As of writing there is still some debate around it, so it is quite messy and
requires more clarity both in specification and in our own implementation.
"""

import datetime
import hashlib
import re
from enum import Enum

import asn1crypto.x509

STASH_LINE_RE = re.compile(r"(\S+) (\S+) (\S+) (\d+)")


def load_cert_stash(stash_path):
    """Load the certificate stash from the file, or None on error.

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
                name, algo, fingerprint, timestamp = match.groups()
                stash[name] = (algo, fingerprint, timestamp, True)
    except (OSError, ValueError):
        return None
    return stash


class CertStatus(Enum):
    """Value returned by validate_cert."""
    # Cert is valid: proceed.
    VALID = 0      # Known and valid.
    VALID_NEW = 7  # New and valid.
    # Cert is unusable or wrong: abort.
    ERROR = 1              # General error.
    WRONG_FINGERPRINT = 2  # Fingerprint in the stash is different.
    # Cert has some issues: ask to proceed.
    NOT_VALID_YET = 3  # not-before date invalid.
    EXPIRED = 4        # not-after date invalid.
    BAD_DOMAIN = 5     # Host name is not in cert's valid domains.


CERT_STATUS_INVALID = (
    CertStatus.NOT_VALID_YET,
    CertStatus.EXPIRED,
    CertStatus.BAD_DOMAIN,
)


def validate_cert(der, hostname, cert_stash):
    """Return a tuple (CertStatus, Certificate) for this certificate."""
    if der is None:
        return CertStatus.ERROR, None
    try:
        cert = asn1crypto.x509.Certificate.load(der)
    except ValueError:
        return CertStatus.ERROR, None
    
    # Check for sane parameters.
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if now < cert.not_valid_before:
        return CertStatus.NOT_VALID_YET, cert
    if now > cert.not_valid_after:
        return CertStatus.EXPIRED, cert
    if hostname not in cert.valid_domains:
        return CertStatus.BAD_DOMAIN, cert

    # Check the entire certificate fingerprint.
    cert_hash = hashlib.sha512(der).hexdigest()
    if hostname in cert_stash:
        _, fingerprint, timestamp, _ = cert_stash[hostname]
        if timestamp >= now.timestamp():
            if cert_hash != fingerprint:
                return CertStatus.WRONG_FINGERPRINT, cert
        else:
            # Disregard expired fingerprints.
            pass
        return CertStatus.VALID, cert

    # The certificate is unknown and valid.
    return CertStatus.VALID_NEW, cert


def trust(cert_stash, hostname, algo, fingerprint, timestamp,
          trust_always=False):
    cert_stash[hostname] = (algo, fingerprint, timestamp, trust_always)
