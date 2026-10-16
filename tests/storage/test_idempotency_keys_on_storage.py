"""
Idempotency keys on every storage (1174): a platform collection that an
unscoped request reaches, a stored answer read back by a retry, exactly one
winner among concurrent requests with one key (a new key and a key free
for take-over alike, also with a pool of separate Postgres connections),
and the purge by `expires_at`.
"""

import threading
from collections.abc import Callable

from app.repositories.idempotency_key_repository import IdempotencyKeyRepository
from app.schemas.constants.idempotency import (
    IdempotencyClaimVerdict,
    IdempotencyRecordStatus,
)
from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.dto.idempotency import (
    IdempotencyClaimDecision,
    IdempotentRequestOutcome,
    StoredResponse,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.idempotency.constrained_integers import StoredResponseStatus
from app.schemas.typings.idempotency.constrained_strings import StoredResponseMediaType
from app.schemas.typings.idempotency.strings import StoredResponseBody
from app.use_cases.idempotency.claim_idempotency_key_use_case import (
    ClaimIdempotencyKeyUseCase,
)
from app.use_cases.idempotency.finish_idempotent_request_use_case import (
    FinishIdempotentRequestUseCase,
)
from tests.e2e.edge_fakes import MovableClock
from tests.idempotency.idempotency_world import OTHER_OWNER, START, claim_of
from tests.storage.conftest import CollectionFactory

# As many as the test pool has connections, so the claims really overlap.
PARALLEL_RETRIES: int = 8
ANSWER: StoredResponse = StoredResponse(
    status=StoredResponseStatus(201),
    media_type=StoredResponseMediaType("application/json"),
    body=StoredResponseBody('{"message":{"id":"message_1","text":"Здравствуйте"}}'),
)


class KeyStore:
    def __init__(self, collections: CollectionFactory) -> None:
        self.clock: MovableClock = MovableClock(START)
        self.repo: IdempotencyKeyRepository = IdempotencyKeyRepository(
            collections(IdempotencyKeyDocument, "idempotency_keys")
        )
        self.claim: ClaimIdempotencyKeyUseCase = ClaimIdempotencyKeyUseCase(
            self.repo, self.clock.wall_clock
        )
        self.finish: FinishIdempotentRequestUseCase = FinishIdempotentRequestUseCase(
            self.repo, self.clock.wall_clock
        )

    def proceed(self) -> IdempotencyClaimDecision:
        decision = self.claim.run(claim_of())
        assert decision.verdict is IdempotencyClaimVerdict.PROCEED
        return decision

    def settle(
        self, decision: IdempotencyClaimDecision, response: StoredResponse | None
    ) -> None:
        assert decision.claim_id is not None
        self.finish.run(
            IdempotentRequestOutcome(
                record_id=decision.record_id,
                claim_id=decision.claim_id,
                response=response,
            )
        )

    def stored(self, decision: IdempotencyClaimDecision) -> IdempotencyKeyDocument:
        record = self.repo.get(decision.record_id)
        assert record is not None
        return record


def race(count: int, action: Callable[[], str]) -> list[str]:
    """Run `action` in `count` threads released at once; their outcomes."""

    outcomes: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    start = threading.Barrier(count)

    def run() -> None:
        start.wait()
        try:
            outcome = action()
        except BaseException as error:  # noqa: BLE001 - reported below
            with lock:
                errors.append(error)
            return
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=run) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    return sorted(outcomes)


def claim_outcome(store: KeyStore) -> str:
    try:
        return store.claim.run(claim_of()).verdict.value
    except ConflictError as refused:
        return str(refused.reasons[0].code)


def test_an_unscoped_request_claims_and_a_retry_replays_the_answer(
    collections: CollectionFactory,
) -> None:
    store = KeyStore(collections)
    decision = store.proceed()

    store.settle(decision, ANSWER)
    replay = store.claim.run(claim_of())

    assert replay.verdict is IdempotencyClaimVerdict.REPLAY
    assert replay.response == ANSWER
    assert store.stored(decision).status is IdempotencyRecordStatus.COMPLETED


def test_of_concurrent_requests_with_a_new_key_exactly_one_runs(
    collections: CollectionFactory,
) -> None:
    store = KeyStore(collections)

    outcomes = race(PARALLEL_RETRIES, lambda: claim_outcome(store))

    assert outcomes == ["in_progress"] * (PARALLEL_RETRIES - 1) + ["proceed"]


def test_of_concurrent_retries_of_a_released_key_exactly_one_takes_it_over(
    collections: CollectionFactory,
) -> None:
    store = KeyStore(collections)
    store.settle(store.proceed(), None)

    outcomes = race(PARALLEL_RETRIES, lambda: claim_outcome(store))

    assert outcomes == ["in_progress"] * (PARALLEL_RETRIES - 1) + ["proceed"]


def test_an_answer_after_a_take_over_is_dropped(
    collections: CollectionFactory,
) -> None:
    store = KeyStore(collections)
    abandoned = store.proceed()
    store.clock.advance(5 * 60)
    retry = store.proceed()

    store.settle(abandoned, ANSWER)

    record = store.stored(retry)
    assert record.claim_id == retry.claim_id
    assert record.status is IdempotencyRecordStatus.IN_PROGRESS
    assert record.response_body is None


def test_the_purge_deletes_only_records_that_expired(
    collections: CollectionFactory,
) -> None:
    store = KeyStore(collections)
    kept = store.proceed()
    store.settle(kept, ANSWER)
    released = store.claim.run(claim_of(user_id=OTHER_OWNER))
    store.settle(released, None)
    store.clock.advance(1)

    deleted = store.repo.delete_expired_before(store.clock.wall_clock.now_unix())

    assert int(deleted) == 1
    assert store.repo.get(released.record_id) is None
    assert store.stored(kept).status is IdempotencyRecordStatus.COMPLETED
