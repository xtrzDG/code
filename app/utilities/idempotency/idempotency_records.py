"""
Idempotency key records: their id, derived from the user and the key, and
when a record no longer holds its key.
"""

from uuid import UUID, uuid5

from typed_time_provider import Microseconds

from app.schemas.constants.idempotency import IdempotencyRecordStatus
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.typings.idempotency.constrained_strings import IdempotencyKey
from app.schemas.typings.idempotency.prefixed_id import IdempotencyRecordId
from app.schemas.typings.users.prefixed_id import UserId

IDEMPOTENCY_RECORD_NAMESPACE: UUID = UUID("6f1d3b2a-9c4e-4d8b-a7f1-2e5c8b0d4a93")


def idempotency_record_id(user_id: UserId, key: IdempotencyKey) -> IdempotencyRecordId:
    """The record of a user's key: one id per (user, key), keys of others apart."""

    return IdempotencyRecordId(uuid5(IDEMPOTENCY_RECORD_NAMESPACE, f"{user_id}\n{key}"))


def is_free(record: IdempotencyKeyDocument, now: Microseconds) -> bool:
    """
    True when the record no longer holds its key at `now`: it expired (24
    hours passed, or its request failed and released it), or its request
    still counts as running past its lease (its process died mid-request).
    """

    if int(record.expires_at) <= int(now):
        return True

    return record.status is IdempotencyRecordStatus.IN_PROGRESS and int(
        record.lease_expires_at
    ) <= int(now)
