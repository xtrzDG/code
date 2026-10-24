"""
The SHA-1 digest Flitt's API prescribes for request and callback signatures.

Flitt (Fondy-compatible) defines `signature = sha1("<secret>|<values>")`;
the platform cannot choose another algorithm without breaking payments.
The digest authenticates messages exchanged with Flitt only; nothing is
stored with it. This file is excluded from CodeQL's analysis
(.github/workflows/codeql.yml) because its weak-hash query cannot know the
algorithm is fixed by the provider; keep this module limited to this one
function.
"""

import hashlib


def flitt_sha1_hex(text: str) -> str:
    """Lowercase hex SHA-1 of the UTF-8 text, as Flitt's signatures use."""

    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()
