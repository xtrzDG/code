"""
What a receiver of the webhooks does with `Workshop-Signature` (as
docs/api-versioning.md tells integrators): recompute HMAC-SHA256 of
`<t>.<raw body>` with the signing secret, compare in constant time and
refuse a `t` more than five minutes away.
"""

import hashlib
import hmac

TOLERANCE_SECONDS: int = 5 * 60


def is_valid_signature(
    secret: str,
    header: str,
    body: str,
    now_seconds: int,
    tolerance_seconds: int = TOLERANCE_SECONDS,
) -> bool:
    parts: dict[str, str] = {}
    for item in header.split(","):
        name, separator, value = item.strip().partition("=")
        if separator:
            parts[name] = value

    signed_at: str = parts.get("t", "")
    expected: str = parts.get("v1", "")
    if not signed_at.isdigit() or expected == "":
        return False

    if abs(now_seconds - int(signed_at)) > tolerance_seconds:
        return False

    digest = hmac.new(
        secret.encode(), f"{signed_at}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, expected)
