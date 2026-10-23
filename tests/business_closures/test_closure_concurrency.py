"""
Racing requests on one closure, started together at a barrier: two owners
closing open one closure; a cancel and the sweep never both win, so a
business is never deleted after its owner cancelled, nor restored after
its deletion was queued.
"""

import threading
from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.in_memory_queued_job_claim_adapter import (
    InMemoryQueuedJobClaimAdapter,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.repositories.business_closure_repositories import BusinessClosureRepository
from app.repositories.job_repositories import QueuedJobRepository
from app.schemas.constants.business_closures import BusinessClosureReason
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.businesses.closure.closure_cancellation import (
    take_pending_closure,
)
from app.use_cases.businesses.closure.queue_due_deletions_use_case import (
    QueueDueDeletionsUseCase,
)
from app.utilities.business_closures.closure_identity import closure_id_for

ROUNDS: int = 40
NOW: Microseconds = Microseconds(1_790_000_000_000_000)


class Queue(JobQueueFacilitatorContract):
    def __init__(self) -> None:
        self.queued: list[str] = []

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        self.queued.append(str(payload))
        return QueuedJobId()


def no_jobs() -> QueuedJobRepository:
    jobs = InMemoryDocumentCollectionAdapter(QueuedJobDocument)
    return QueuedJobRepository(jobs, InMemoryQueuedJobClaimAdapter(jobs))


def due_closure(business_id: BusinessId) -> BusinessClosureDocument:
    return BusinessClosureDocument(
        id=closure_id_for(business_id),
        business_id=business_id,
        reason=BusinessClosureReason.OWNER_REQUEST,
        requested_at=Microseconds(int(NOW) - 1),
        delete_after=Microseconds(int(NOW) - 1),
        status_before=BusinessStatus.LIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def race(first: Callable[[], bool], second: Callable[[], bool]) -> list[bool]:
    """Run both from one barrier; their answers, first's then second's."""

    barrier = threading.Barrier(2)
    answers: dict[int, bool] = {}

    def run(index: int, step: Callable[[], bool]) -> None:
        barrier.wait()
        answers[index] = step()

    threads = [
        threading.Thread(target=run, args=(index, step))
        for index, step in enumerate((first, second))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return [answers[0], answers[1]]


def repository() -> BusinessClosureRepository:
    return BusinessClosureRepository(
        InMemoryDocumentCollectionAdapter(BusinessClosureDocument)
    )


def open_twice() -> list[bool]:
    closures, business_id = repository(), BusinessId()
    return race(
        lambda: closures.open(due_closure(business_id)),
        lambda: closures.open(due_closure(business_id)),
    )


def cancel_while_sweeping() -> tuple[bool, bool, BusinessClosureDocument, Queue]:
    """Whether the cancel won, whether the sweep queued, and what is stored."""

    clock = WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: int(NOW) * 1000,
    )
    closures, business_id, queue = repository(), BusinessId(), Queue()
    closures.open(due_closure(business_id))
    sweep = QueueDueDeletionsUseCase(closures, queue, no_jobs(), clock)
    tick = JobTick(job_name=JobName("queue_business_deletions"), scheduled_at=NOW)
    cancelled, queued = race(
        lambda: take_pending_closure(closures, business_id, NOW) is not None,
        lambda: int(sweep.run(tick).processed_count) == 1,
    )
    stored = closures.get(business_id)
    assert stored is not None
    return cancelled, queued, stored, queue


def test_two_owners_closing_at_once_open_one_closure() -> None:
    for _ in range(ROUNDS):
        assert sorted(open_twice()) == [False, True]


def test_a_cancel_and_the_sweep_never_both_win() -> None:
    for _ in range(ROUNDS):
        cancelled, queued, stored, queue = cancel_while_sweeping()

        assert cancelled != queued
        assert (stored.cancelled_at is not None) is cancelled
        assert (stored.deletion_queued_at is not None) is queued
        assert len(queue.queued) == int(queued)
