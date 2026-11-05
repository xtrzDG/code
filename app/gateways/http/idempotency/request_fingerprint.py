"""What a creating request asked for, as one SHA-256 (its idempotency fingerprint)."""

import hashlib
import json

from app.gateways.http.json_nesting import MAX_JSON_NESTING_DEPTH, json_nesting_depth
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
    retry is not refused; any other body counts byte for byte (so does a
    body nested deeper than the request limit, which is never parsed: its
    route refuses it with 422 `too_deep`).
    """

    digest = hashlib.sha256()
    for part in (method.upper(), path, query):
        digest.update(part.encode())
        digest.update(FIELD_SEPARATOR)
    digest.update(canonical_body(body))
    return IdempotencyRequestFingerprint(digest.hexdigest())


def canonical_body(body: bytes) -> bytes:
    if not body:
        return b""

    if json_nesting_depth(body) > MAX_JSON_NESTING_DEPTH:
        return body

    try:
        parsed: object = json.loads(body)
    except ValueError:
        return body

    # A lone surrogate (an escaped "\ud800") is valid JSON but no UTF-8:
    # it is kept as its own bytes rather than failing the request.
    return json.dumps(
        parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8", "surrogatepass")
