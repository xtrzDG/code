"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class IdempotencyKey(BaseConstrainedTypedString):
    """
    The `Idempotency-Key` header of a creating request: a value the client
    chooses once per action (a UUID is best) and sends again on every retry
    of it. Visible ASCII, up to 255 characters. Keys are scoped to the user
    who sends them and live for 24 hours.

    Example:
        key = IdempotencyKey("4b0e2a5c-7d1f-4e8a-9c3b-1f2e3d4c5b6a")
    """

    min_length = 1
    max_length = 255
    pattern = r"^[\x21-\x7e]+$"


class IdempotencyRequestFingerprint(BaseConstrainedTypedString):
    """
    SHA-256 hex digest of what a creating request asked for: its method,
    path and body (JSON compared by meaning, not by spacing or key order).
    A retry with the same key must carry the same fingerprint.

    Example:
        fingerprint = IdempotencyRequestFingerprint("ab" * 32)
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class IdempotentOperation(BaseConstrainedTypedString):
    """
    The operation an idempotency key was used for: the method and the route
    template, e.g. "POST /v1/businesses/{business_id}/bookings".

    Example:
        operation = IdempotentOperation("POST /v1/assistants")
    """

    min_length = 6
    max_length = 300
    pattern = r"^(POST|PUT|PATCH|DELETE) /[\x21-\x7e]*$"


class StoredResponseMediaType(BaseConstrainedTypedString):
    """
    The Content-Type of a stored answer, replayed as it was sent.

    Example:
        media_type = StoredResponseMediaType("application/json")
    """

    min_length = 3
    max_length = 120
    pattern = r"^[\x20-\x7e]+$"


# Keep abc order for all non example types, if possible.
