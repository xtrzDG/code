from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.repositories.idempotency_repositories import (
    IdempotencyKeyRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.idempotency import (
    IdempotencyClaimVerdict,
    IdempotencyRecordStatus,
    IdempotencyRefusalCode,
)
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.dto.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimDecision,
    StoredResponse,
)
from app.schemas.typings.idempotency.prefixed_id import IdempotencyClaimId
from app.use_cases.idempotency.idempotency_refusals import build_refusal
from app.utilities.idempotency.idempotency_records import (
    idempotency_record_id,
    is_free,
)

# A key and its stored answer are kept for a day after the first request.
IDEMPOTENCY_KEY_LIFETIME: Seconds = Seconds(24 * 60 * 60)
# A request holds its key this long at most: a claim older than that was
# left by a process that died mid-request, and the next retry takes it
# over. Far above the slowest creating request (provider calls time out
# within a minute).
IDEMPOTENCY_CLAIM_LEASE: Seconds = Seconds(5 * 60)


class ClaimIdempotencyKeyUseCase(
    UseCaseContract[IdempotencyClaim, IdempotencyClaimDecision]
):
    """
    Decide what a creating request with an Idempotency-Key may do, before
    it runs.

    - A new key (or one that is free again: expired after its day,
      released by a failed request, or left by a dead process past its
      lease) is claimed for this request: PROCEED.
    - A key used for a different request (another operation, path or
      body): ConflictError, reason `idempotency_key_reused`.
    - A key whose first request is still running: ConflictError, reason
      `in_progress`.
    - A key whose first request succeeded: REPLAY with its stored answer.

    Claiming is one atomic insert, or one atomic take-over of a free
    record, so of two concurrent requests with the same key exactly one
    proceeds and the other is told the first is in progress, also across
    processes.
    """

    def __init__(
        self,
        idempotency_key_repo: IdempotencyKeyRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._idempotency_key_repo: IdempotencyKeyRepoContract = idempotency_key_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: IdempotencyClaim) -> IdempotencyClaimDecision:
        now: Microseconds = self._wall_clock.now_unix()
        record: IdempotencyKeyDocument = self._new_record(input_data, now)
        if self._idempotency_key_repo.insert_if_new(record):
            return proceed(record)

        stored: IdempotencyKeyDocument | None = self._idempotency_key_repo.get(
            record.id
        )
        if stored is None:
            # Purged between the insert and the read: claim it once more.
            if self._idempotency_key_repo.insert_if_new(record):
                return proceed(record)
            raise build_refusal(IdempotencyRefusalCode.IN_PROGRESS)

        if is_free(stored, now):
            if self._idempotency_key_repo.take_over_if_free(record, now):
                return proceed(record)
            # A concurrent retry took it over first and runs now.
            raise build_refusal(IdempotencyRefusalCode.IN_PROGRESS)

        return decide_on_held_key(stored, input_data)

    def _new_record(
        self, claim: IdempotencyClaim, now: Microseconds
    ) -> IdempotencyKeyDocument:
        return IdempotencyKeyDocument(
            id=idempotency_record_id(claim.user_id, claim.key),
            user_id=claim.user_id,
            operation=claim.operation,
            fingerprint=claim.fingerprint,
            claim_id=IdempotencyClaimId(),
            lease_expires_at=self._wall_clock.now_unix_with_delta(
                IDEMPOTENCY_CLAIM_LEASE
            ),
            expires_at=self._wall_clock.now_unix_with_delta(IDEMPOTENCY_KEY_LIFETIME),
            created_at=now,
            updated_at=now,
        )


def proceed(record: IdempotencyKeyDocument) -> IdempotencyClaimDecision:
    return IdempotencyClaimDecision(
        verdict=IdempotencyClaimVerdict.PROCEED,
        record_id=record.id,
        claim_id=record.claim_id,
    )


def decide_on_held_key(
    stored: IdempotencyKeyDocument, claim: IdempotencyClaim
) -> IdempotencyClaimDecision:
    """The answer for a key another request holds or has completed."""

    is_same_request: bool = (
        stored.user_id == claim.user_id
        and stored.operation == claim.operation
        and stored.fingerprint == claim.fingerprint
    )
    if not is_same_request:
        raise build_refusal(IdempotencyRefusalCode.KEY_REUSED)

    response: StoredResponse | None = stored_response(stored)
    if stored.status is IdempotencyRecordStatus.IN_PROGRESS or response is None:
        raise build_refusal(IdempotencyRefusalCode.IN_PROGRESS)

    return IdempotencyClaimDecision(
        verdict=IdempotencyClaimVerdict.REPLAY,
        record_id=stored.id,
        response=response,
    )


def stored_response(record: IdempotencyKeyDocument) -> StoredResponse | None:
    if (
        record.response_status is None
        or record.response_media_type is None
        or record.response_body is None
    ):
        return None

    return StoredResponse(
        status=record.response_status,
        media_type=record.response_media_type,
        body=record.response_body,
    )
