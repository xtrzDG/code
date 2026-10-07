"""What the gateway and the idempotency use cases tell each other."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.idempotency import IdempotencyClaimVerdict
from app.schemas.typings.idempotency.constrained_integers import StoredResponseStatus
from app.schemas.typings.idempotency.constrained_strings import (
    IdempotencyKey,
    IdempotencyRequestFingerprint,
    IdempotentOperation,
    StoredResponseMediaType,
)
from app.schemas.typings.idempotency.prefixed_id import (
    IdempotencyClaimId,
    IdempotencyRecordId,
)
from app.schemas.typings.idempotency.strings import StoredResponseBody
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId


class IdempotencyClaim(ImmutableDTO):
    """
    A signed-in user's creating request with an Idempotency-Key, before it
    runs. `api_key_id`: the key a public API request came with; each key
    keeps its own Idempotency-Keys (its owner's other keys never meet them).
    """

    user_id: UserId
    key: IdempotencyKey
    operation: IdempotentOperation
    fingerprint: IdempotencyRequestFingerprint
    api_key_id: ApiKeyId | None = None


class StoredResponse(ImmutableDTO):
    """The successful answer of a creating request, as it was sent."""

    status: StoredResponseStatus
    media_type: StoredResponseMediaType
    body: StoredResponseBody


class IdempotencyClaimDecision(ImmutableDTO):
    """
    PROCEED: the request holds the key under `claim_id` and runs; REPLAY:
    answer with `response`, the stored answer of the first request.
    """

    verdict: IdempotencyClaimVerdict
    record_id: IdempotencyRecordId
    claim_id: IdempotencyClaimId | None = None
    response: StoredResponse | None = None


class IdempotentRequestOutcome(ImmutableDTO):
    """
    How a request that held a key ended: its answer to keep (a success), or
    None, which releases the key so the retry runs again.
    """

    record_id: IdempotencyRecordId
    claim_id: IdempotencyClaimId
    response: StoredResponse | None = None
