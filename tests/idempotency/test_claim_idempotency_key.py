"""
What a creating request with an Idempotency-Key may do: run once, replay its
stored answer, or be refused (another body, still running), and how a key
frees up again (released by a failure, past the lease, after its day).
"""

import threading

import pytest

from app.schemas.constants.idempotency import (
    IdempotencyClaimVerdict,
    IdempotencyRecordStatus,
)
from app.schemas.dto.idempotency import (
    IdempotencyClaimDecision,
    IdempotentRequestOutcome,
    StoredResponse,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.idempotency.constrained_integers import StoredResponseStatus
from app.schemas.typings.idempotency.constrained_strings import (
    IdempotentOperation,
    StoredResponseMediaType,
)
from app.schemas.typings.idempotency.strings import StoredResponseBody
from app.schemas.typings.platform.constrained_strings import JobName
from tests.idempotency.idempotency_world import (
    OTHER_BODY,
    OTHER_OWNER,
    IdempotencyWorld,
    claim_of,
)

ANSWER: StoredResponse = StoredResponse(
    status=StoredResponseStatus(201),
    media_type=StoredResponseMediaType("application/json"),
    body=StoredResponseBody('{"booking":{"id":"booking_1"}}'),
)
HOUR: int = 60 * 60


def refusal_code(error: ConflictError) -> str:
    return str(error.reasons[0].code)


def proceed(world: IdempotencyWorld) -> IdempotencyClaimDecision:
    decision = world.claim_use_case().run(claim_of())
    assert decision.verdict is IdempotencyClaimVerdict.PROCEED
    assert decision.claim_id is not None
    return decision


def finish(
    world: IdempotencyWorld,
    decision: IdempotencyClaimDecision,
    response: StoredResponse | None,
) -> None:
    assert decision.claim_id is not None
    world.finish_use_case().run(
        IdempotentRequestOutcome(
            record_id=decision.record_id,
            claim_id=decision.claim_id,
            response=response,
        )
    )


def test_a_new_key_lets_the_request_run_and_holds_the_key() -> None:
    world = IdempotencyWorld()

    decision = proceed(world)

    [record] = world.records()
    assert record.id == decision.record_id
    assert record.status is IdempotencyRecordStatus.IN_PROGRESS
    assert record.response_body is None


def test_a_retry_after_success_replays_the_stored_answer() -> None:
    world = IdempotencyWorld()
    finish(world, proceed(world), ANSWER)

    replay = world.claim_use_case().run(claim_of())

    assert replay.verdict is IdempotencyClaimVerdict.REPLAY
    assert replay.response == ANSWER
    assert world.records()[0].status is IdempotencyRecordStatus.COMPLETED


def test_the_same_key_with_another_body_is_refused_as_reused() -> None:
    world = IdempotencyWorld()
    finish(world, proceed(world), ANSWER)

    with pytest.raises(ConflictError) as refused:
        world.claim_use_case().run(claim_of(fingerprint=OTHER_BODY))

    assert refusal_code(refused.value) == "idempotency_key_reused"


def test_the_same_key_on_another_operation_is_refused_as_reused() -> None:
    world = IdempotencyWorld()
    proceed(world)

    with pytest.raises(ConflictError) as refused:
        world.claim_use_case().run(
            claim_of(operation=IdempotentOperation("POST /v1/assistants"))
        )

    assert refusal_code(refused.value) == "idempotency_key_reused"


def test_a_retry_while_the_first_request_runs_is_refused_as_in_progress() -> None:
    world = IdempotencyWorld()
    proceed(world)

    with pytest.raises(ConflictError) as refused:
        world.claim_use_case().run(claim_of())

    assert refusal_code(refused.value) == "in_progress"


def test_keys_of_different_users_never_meet() -> None:
    world = IdempotencyWorld()
    proceed(world)

    other = world.claim_use_case().run(claim_of(user_id=OTHER_OWNER))

    assert other.verdict is IdempotencyClaimVerdict.PROCEED
    assert len(world.records()) == 2


def test_a_failed_request_releases_its_key_and_the_retry_runs_again() -> None:
    world = IdempotencyWorld()
    finish(world, proceed(world), None)

    retry = world.claim_use_case().run(claim_of(fingerprint=OTHER_BODY))

    assert retry.verdict is IdempotencyClaimVerdict.PROCEED
    assert world.records()[0].fingerprint == OTHER_BODY


def test_a_claim_past_its_lease_is_taken_over_and_the_late_answer_dropped() -> None:
    world = IdempotencyWorld()
    abandoned = proceed(world)
    world.clock.advance(5 * 60)

    retry = proceed(world)
    finish(world, abandoned, ANSWER)

    [record] = world.records()
    assert retry.claim_id != abandoned.claim_id
    assert record.claim_id == retry.claim_id
    assert record.status is IdempotencyRecordStatus.IN_PROGRESS


def test_a_slow_request_nobody_took_over_still_stores_its_answer() -> None:
    world = IdempotencyWorld()
    slow = proceed(world)
    world.clock.advance(10 * 60)

    finish(world, slow, ANSWER)

    assert world.records()[0].status is IdempotencyRecordStatus.COMPLETED


def test_a_key_lives_a_day_then_counts_as_new() -> None:
    world = IdempotencyWorld()
    finish(world, proceed(world), ANSWER)
    world.clock.advance(24 * HOUR - 1)
    replay = world.claim_use_case().run(claim_of())
    world.clock.advance(1)

    fresh = world.claim_use_case().run(claim_of(fingerprint=OTHER_BODY))

    assert replay.verdict is IdempotencyClaimVerdict.REPLAY
    assert fresh.verdict is IdempotencyClaimVerdict.PROCEED


def test_of_concurrent_retries_exactly_one_runs() -> None:
    world = IdempotencyWorld()
    use_case = world.claim_use_case()
    start = threading.Barrier(8)
    verdicts: list[str] = []
    lock = threading.Lock()

    def claim() -> None:
        start.wait()
        try:
            outcome = use_case.run(claim_of()).verdict.value
        except ConflictError as refused:
            outcome = refusal_code(refused)
        with lock:
            verdicts.append(outcome)

    threads = [threading.Thread(target=claim) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(verdicts) == ["in_progress"] * 7 + ["proceed"]


def test_the_purge_deletes_expired_and_released_keys_and_is_audited() -> None:
    world = IdempotencyWorld()
    finish(world, proceed(world), ANSWER)
    finish(world, world.claim_use_case().run(claim_of(user_id=OTHER_OWNER)), None)
    world.clock.advance(1)
    tick = JobTick(
        job_name=JobName("purge_idempotency_keys"),
        scheduled_at=world.clock.wall_clock.now_unix(),
    )

    first = world.purge_use_case().run(tick)
    world.clock.advance(24 * HOUR)
    second = world.purge_use_case().run(tick)
    third = world.purge_use_case().run(tick)

    assert [int(report.processed_count) for report in (first, second, third)] == [
        1,
        1,
        0,
    ]
    assert world.records() == []
    entries = world.audit_collection.list_all()
    assert [(entry.action.value, str(entry.entity)) for entry in entries] == [
        ("retention_purge", "idempotency_key"),
        ("retention_purge", "idempotency_key"),
    ]
    assert all(entry.business_id is None for entry in entries)
