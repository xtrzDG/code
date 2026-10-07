"""
Job wake-ups between processes through Postgres NOTIFY / LISTEN: the queue
signals in the job's own transaction, so a worker hears of the job only
once it is committed, and within milliseconds.
"""

from collections.abc import Generator

import psycopg
import pytest

from app.adapters.jobs.postgres_job_wakeup_adapter import (
    JOB_WAKEUP_CHANNEL,
    PostgresJobWakeupAdapter,
    connect_wakeup_listener,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.postgres.postgres_notification_listener import ListenerConnection
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import DatabaseUrl, JobPayloadJson
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.job_stores import build_postgres_job_stores
from tests.storage.storage_testing import build_fixed_wall_clock

PROCESS_INBOUND_MESSAGE: JobName = JobName("process_inbound_message")
EMPTY_PAYLOAD: JobPayloadJson = JobPayloadJson("{}")
# Generous for a loaded CI machine; a wake-up normally takes a few ms.
WAKEUP_SECONDS: float = 10.0
# Long enough for a notification that should not come.
SILENCE_SECONDS: float = 0.3


@pytest.fixture
def worker_wakeup(
    database_url: DatabaseUrl,
) -> Generator[PostgresJobWakeupAdapter]:
    """The wake-up of a worker process: its own pool and LISTEN session."""

    pool = PostgresConnectionPoolClient(database_url, max_size=2)
    wakeup = PostgresJobWakeupAdapter(
        connection_pool=pool, connect=lambda: connect_wakeup_listener(database_url)
    )
    try:
        with wakeup.listen():
            # LISTEN in place wakes every lane once (missed signals).
            for lane in JobLane:
                assert wakeup.wait(lane, 10.0), lane
            yield wakeup
    finally:
        pool.close()


def build_api_queue(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> tuple[JobQueueFacilitator, PostgresUnitOfWorkAdapter]:
    """The queue of an API process: NOTIFY on its pool, in a unit of work."""

    stores = build_postgres_job_stores(connection_pool, postgres_collections)
    unit_of_work = PostgresUnitOfWorkAdapter(connection_pool, storage_scope)
    api_wakeup = PostgresJobWakeupAdapter(
        connection_pool=connection_pool,
        connect=lambda: pytest.fail("the API process never listens"),
    )
    queue = JobQueueFacilitator(
        job_repo=stores.job_repo,
        wall_clock=build_fixed_wall_clock(),
        job_wakeup=api_wakeup,
        unit_of_work=unit_of_work,
    )
    return queue, unit_of_work


def test_a_job_queued_by_one_process_wakes_another_at_once(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
    worker_wakeup: PostgresJobWakeupAdapter,
) -> None:
    queue, _ = build_api_queue(connection_pool, postgres_collections, platform_scope)

    queue.enqueue(
        PROCESS_INBOUND_MESSAGE, EMPTY_PAYLOAD, business_id=None, lane=JobLane.INBOUND
    )

    # Nothing but the queue's NOTIFY can wake the lane here (no poll, no
    # timer), so a wake-up at all is the notification arriving.
    assert worker_wakeup.wait(JobLane.INBOUND, WAKEUP_SECONDS)
    # Only the job's lane: the outbound lane's threads keep waiting.
    assert not worker_wakeup.wait(JobLane.OUTBOUND, SILENCE_SECONDS)


def test_the_wakeup_leaves_only_when_the_job_commits(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
    worker_wakeup: PostgresJobWakeupAdapter,
) -> None:
    queue, unit_of_work = build_api_queue(
        connection_pool, postgres_collections, platform_scope
    )

    with unit_of_work.unit_of_work():
        queue.enqueue(
            PROCESS_INBOUND_MESSAGE,
            EMPTY_PAYLOAD,
            business_id=None,
            lane=JobLane.INBOUND,
        )
        # Inside the transaction nobody hears of the job yet.
        assert not worker_wakeup.wait(JobLane.INBOUND, SILENCE_SECONDS)

    assert worker_wakeup.wait(JobLane.INBOUND, WAKEUP_SECONDS)


def test_a_rolled_back_job_wakes_nobody(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
    worker_wakeup: PostgresJobWakeupAdapter,
) -> None:
    queue, unit_of_work = build_api_queue(
        connection_pool, postgres_collections, platform_scope
    )

    with pytest.raises(RuntimeError), unit_of_work.unit_of_work():
        queue.enqueue(
            PROCESS_INBOUND_MESSAGE,
            EMPTY_PAYLOAD,
            business_id=None,
            lane=JobLane.INBOUND,
        )
        raise RuntimeError("the request failed after queuing")

    assert not worker_wakeup.wait(JobLane.INBOUND, SILENCE_SECONDS)


def test_signals_of_an_unknown_lane_are_ignored(
    database_url: DatabaseUrl,
    worker_wakeup: PostgresJobWakeupAdapter,
) -> None:
    with psycopg.connect(str(database_url), autocommit=True) as connection:
        connection.execute(
            "select pg_notify(%s, %s)", (JOB_WAKEUP_CHANNEL, "lane_of_a_newer_release")
        )
        connection.execute("select pg_notify(%s, %s)", (JOB_WAKEUP_CHANNEL, "outbound"))

    assert worker_wakeup.wait(JobLane.OUTBOUND, WAKEUP_SECONDS)
    assert not worker_wakeup.wait(JobLane.INBOUND, SILENCE_SECONDS)


def test_a_lost_listen_session_reconnects_and_wakes_every_lane(
    database_url: DatabaseUrl,
) -> None:
    attempts: list[int] = []

    def connect() -> ListenerConnection:
        attempts.append(1)
        if len(attempts) == 1:
            raise psycopg.OperationalError("the server restarted")

        return connect_wakeup_listener(database_url)

    pool = PostgresConnectionPoolClient(database_url, max_size=1)
    wakeup = PostgresJobWakeupAdapter(connection_pool=pool, connect=connect)
    try:
        with wakeup.listen():
            # Once LISTEN is back, every lane looks at the queue: signals
            # sent while it was away are lost.
            for lane in JobLane:
                assert wakeup.wait(lane, 10.0), lane
    finally:
        pool.close()

    assert len(attempts) == 2
