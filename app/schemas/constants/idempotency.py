"""Idempotency keys of creating requests (docs/api-versioning.md)."""

from enum import StrEnum


class IdempotencyRecordStatus(StrEnum):
    """Where the request that first used a key stands."""

    # It is still running: a retry now gets 409 `in_progress`.
    IN_PROGRESS = "in_progress"
    # It succeeded and its answer is stored: a retry gets that answer.
    COMPLETED = "completed"


class IdempotencyClaimVerdict(StrEnum):
    """What a request carrying an idempotency key may do."""

    # The key is new (or free again): run the request and store its answer.
    PROCEED = "proceed"
    # The key's request succeeded before: answer with the stored response.
    REPLAY = "replay"


class IdempotencyRefusalCode(StrEnum):
    """Machine-readable reasons a request with a used key is refused (409)."""

    # The key was used for a different request (another body or path).
    KEY_REUSED = "idempotency_key_reused"
    # The first request with this key is still running.
    IN_PROGRESS = "in_progress"
