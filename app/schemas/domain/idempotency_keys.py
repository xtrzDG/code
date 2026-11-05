"""
The record of one idempotency key (migration 1174): what the first request
that carried the key asked for and, once it succeeded, its answer, which a
retry with the same key gets instead of a second booking, message, checkout
or assistant (docs/api-versioning.md).
"""

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.idempotency import IdempotencyRecordStatus
from app.schemas.typings.idempotency.constrained_integers import StoredResponseStatus
from app.schemas.typings.idempotency.constrained_strings import (
    IdempotencyRequestFingerprint,
    IdempotentOperation,
    StoredResponseMediaType,
)
from app.schemas.typings.idempotency.prefixed_id import (
    IdempotencyClaimId,
    IdempotencyRecordId,
)
from app.schemas.typings.idempotency.strings import StoredResponseBody
from app.schemas.typings.users.prefixed_id import UserId


class IdempotencyKeyDocument(BaseDocument):
    """
    One idempotency key of one user, keyed by the id derived from both (a
    platform collection: POST /v1/assistants creates a business, so the key
    belongs to no business yet). The key itself is not stored.

    `operation` and `fingerprint` are what the first request asked for; a
    retry must ask for the same. While that request runs the record is
    IN_PROGRESS under its `claim_id` until `lease_expires_at`; a success
    stores its answer (`response_*`) and makes it COMPLETED. A refused or
    failed request releases the key by expiring the record at once, so the
    retry runs again. The record lives until `expires_at` (24 hours after
    the first request); the hourly purge deletes it then, and an expired
    record counts as no record at all.
    """

    id: IdempotencyRecordId
    user_id: UserId
    operation: IdempotentOperation
    fingerprint: IdempotencyRequestFingerprint
    status: IdempotencyRecordStatus = IdempotencyRecordStatus.IN_PROGRESS
    claim_id: IdempotencyClaimId
    lease_expires_at: Microseconds
    expires_at: Microseconds
    response_status: StoredResponseStatus | None = None
    response_media_type: StoredResponseMediaType | None = None
    response_body: StoredResponseBody | None = None
    completed_at: Microseconds | None = None
