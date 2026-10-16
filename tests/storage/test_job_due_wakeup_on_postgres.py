"""
A job queued for later by one process (the burst of a customer's messages,
answered once the customer is quiet) wakes the lane of a listening worker
process at its due time: the NOTIFY carries the due time, leaves only when
the job commits, and the worker's timer wakes the lane then.
"""

import threading
import time
from collections.abc import Generator

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.jobs.postgres_job_wakeup_adapter import (
    PostgresJobWakeupAdapter,
    connect_wakeup_listener,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import DatabaseUrl, JobPayloadJson
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.job_stores import build_postgres_job_stores

PROCESS_INBOUND_MESSAGE: JobName = JobName("process_inbound_message")
EMPTY_PAYLOAD: JobPayloadJson = JobPayloadJson("{}")
WAIT_SECONDS: float = 10.0
SECOND: int = 1_000_000


class AnnouncedDueTimes(JobWakeupSignal):
    """The worker's signal, remembering every due time it was told of."""

    def __init__(self) -> None:
        super().__init__()
        self.due: list[tuple[JobLane, Microseconds]] = []
        self.announced: threading.Event = threading.Event()

    def notify_at(self, lane: JobLane, run_at: Microseconds) -> None:
        self.due.append((lane, run_at))
        self.announced.set()
        super().notify_at(lane, run_at)


@pytest.fixture
def worker_signal(database_url: DatabaseUrl) -> Generator[AnnouncedDueTimes]:
    """A listening worker process: its pool, LISTEN session and timer."""

    signal = AnnouncedDueTimes()
    pool = PostgresConnectionPoolClient(database_url, max_size=2)
    wakeup = PostgresJobWakeupAdapter(
        connection_pool=pool,
        connect=lambda: connect_wakeup_listener(database_url),
        signal=signal,
    )
    try:
        with wakeup.listen():
            # LISTEN in place wakes every lane once (missed signals).
            for lane in JobLane:
                assert wakeup.wait(lane, WAIT_SECONDS), lane
            yield signal
    finally:
        pool.close()


def build_api_queue(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> tuple[JobQueueFacilitator, PostgresUnitOfWorkAdapter]:
    """The queue of an API process, on real time (jobs really become due)."""

    stores = build_postgres_job_stores(connection_pool, postgres_collections)
    unit_of_work = PostgresUnitOfWorkAdapter(connection_pool, storage_scope)
    queue = JobQueueFacilitator(
        job_repo=stores.job_repo,
        wall_clock=WallClock(preferred_time_unit_type=Microseconds),
        job_wakeup=PostgresJobWakeupAdapter(
            connection_pool=connection_pool,
            connect=lambda: pytest.fail("the API process never listens"),
        ),
        unit_of_work=unit_of_work,
    )
    return queue, unit_of_work


def test_a_later_job_wakes_the_worker_lane_at_its_due_time(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
    worker_signal: AnnouncedDueTimes,
) -> None:
    queue, unit_of_work = build_api_queue(
        connection_pool, postgres_collections, platform_scope
    )
    run_at = Microseconds(time.time_ns() // 1_000 + SECOND // 2)

    with unit_of_work.unit_of_work():
        queue.enqueue(
            PROCESS_INBOUND_MESSAGE,
            EMPTY_PAYLOAD,
            business_id=None,
            run_at=run_at,
            lane=JobLane.INBOUND,
        )
        # Inside the transaction the worker has not heard of it.
        assert worker_signal.due == []

    assert worker_signal.announced.wait(WAIT_SECONDS)
    assert worker_signal.due == [(JobLane.INBOUND, run_at)]
    assert worker_signal.wait(JobLane.INBOUND, WAIT_SECONDS)
    # Woken at the due time, not before (the claim would find nothing).
    assert time.time_ns() // 1_000 >= int(run_at)
    # The job's lane only.
    assert not worker_signal.wait(JobLane.OUTBOUND, 0.0)


def test_a_rolled_back_later_job_announces_nothing(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
    worker_signal: AnnouncedDueTimes,
) -> None:
    queue, unit_of_work = build_api_queue(
        connection_pool, postgres_collections, platform_scope
    )

    with pytest.raises(RuntimeError), unit_of_work.unit_of_work():
        queue.enqueue(
            PROCESS_INBOUND_MESSAGE,
            EMPTY_PAYLOAD,
            business_id=None,
            run_at=Microseconds(time.time_ns() // 1_000 + SECOND),
            lane=JobLane.INBOUND,
        )
        raise RuntimeError("the request failed after queuing")

    # A job queued right after it is announced alone: notifications keep
    # their commit order, so nothing of the rolled back one came before.
    queue.enqueue(PROCESS_INBOUND_MESSAGE, EMPTY_PAYLOAD, None, lane=JobLane.OUTBOUND)
    assert worker_signal.wait(JobLane.OUTBOUND, WAIT_SECONDS)
    assert worker_signal.due == []
