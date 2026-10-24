"""
Idempotency key records: their id, derived from the user, the API key a
public API request came with and the key, and when a record no longer
holds its key.
"""

from uuid import UUID, uuid5

from typed_time_provider import Microseconds

from app.schemas.constants.idempotency import IdempotencyRecordStatus
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.typings.idempotency.constrained_strings import IdempotencyKey
from app.schemas.typings.idempotency.prefixed_id import IdempotencyRecordId
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId

IDEMPOTENCY_RECORD_NAMESPACE: UUID = UUID("6f1d3b2a-9c4e-4d8b-a7f1-2e5c8b0d4a93")


def idempotency_record_id(
    user_id: UserId, key: IdempotencyKey, api_key_id: ApiKeyId | None = None
) -> IdempotencyRecordId:
    """
    The record of a user's key: one id per (user, key), keys of others
    apart. A public API request's key is its API key's own: one id per
    (user, API key, key), so the owner's other API keys never meet it.
    """

    name: str = (
        f"{user_id}\n{key}" if api_key_id is None else f"{user_id}\n{api_key_id}\n{key}"
    )
    return IdempotencyRecordId(uuid5(IDEMPOTENCY_RECORD_NAMESPACE, name))


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
