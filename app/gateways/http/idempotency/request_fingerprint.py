"""What a creating request asked for, as one SHA-256 (its idempotency fingerprint)."""

import hashlib
import json

from app.schemas.typings.idempotency.constrained_strings import (
    IdempotencyRequestFingerprint,
)

FIELD_SEPARATOR: bytes = b"\n"


def fingerprint_request(
    method: str, path: str, query: str, body: bytes
) -> IdempotencyRequestFingerprint:
    """
    SHA-256 of the method, the path (with its ids), the query string and the
    body. A JSON body counts by meaning: keys in any order and any spacing
    give the same fingerprint, so a client that rebuilds the same body for a
    retry is not refused; any other body counts byte for byte.
    """

    digest = hashlib.sha256()
    for part in (method.upper().encode(), path.encode(), query.encode()):
        digest.update(part)
        digest.update(FIELD_SEPARATOR)
    digest.update(canonical_body(body))
    return IdempotencyRequestFingerprint(digest.hexdigest())


def canonical_body(body: bytes) -> bytes:
    if not body:
        return b""

    try:
        parsed: object = json.loads(body)
    except ValueError:
        return body

    return json.dumps(
        parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
