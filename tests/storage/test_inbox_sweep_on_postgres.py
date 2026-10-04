"""
The inbox's intake and sweeper on Postgres: an event and its job commit
together or not at all (a crash between the two leaves neither, and the
redelivered webhook stores both), the sweeper finds stale events through
the index of migration 1094, and the job queue tells which of them still
have a job (on either storage).
"""

from collections.abc import Generator
from typing import LiteralString, cast

import pytest
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.jobs import JobQueueFacilitatorContract
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.repositories.delivery_repositories import InboundEventRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import DatabaseUrl, JobPayloadJson
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.shared.inbox_queue import store_and_queue
from app.utilities.deliveries.delivery_jobs import (
    PROCESS_INBOUND_MESSAGE_JOB,
    encode_inbound_event_payload,
)
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.worker_fakes import JobStores
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.hot_path_queries import INDEX_NODE_TYPES
from tests.storage.hot_path_seeding import RecordingConnectionPool, plan_nodes
from tests.storage.job_stores import build_postgres_job_stores, job_stores_for
from tests.storage.storage_testing import build_fixed_wall_clock

SECOND: int = 1_000_000
SWEEP_INDEX: str = "inbound_events_doc_status_created_at_idx"


def event(
    business_id: BusinessId, message_id: str, created_at: int = 0
) -> InboundEventDocument:
    provider_message_id = ProviderMessageId(message_id)
    return InboundEventDocument(
        id=derive_inbound_event_id(
            business_id, ChannelKind.TELEGRAM, provider_message_id
        ),
        business_id=business_id,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=ChannelKind.TELEGRAM,
        provider_message_id=provider_message_id,
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


class CrashAfterQueuing(JobQueueFacilitatorContract):
    """Queues the job, then the process loses its database connection."""

    def __init__(self, queue: JobQueueFacilitatorContract) -> None:
        self._queue: JobQueueFacilitatorContract = queue

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        self._queue.enqueue(job_name, payload, business_id, run_at, lane, serial_key)
        raise ExternalServiceError("database connection lost")


class Intake:
    """The inbox, the job queue and a unit of work of an API process."""

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        postgres_collections: PostgresCollectionFactory,
        storage_scope: StorageScopeContext,
    ) -> None:
        self.events = InboundEventRepository(
            postgres_collections(InboundEventDocument, "inbound_events")
        )
        self.jobs: JobStores = build_postgres_job_stores(
            connection_pool, postgres_collections
        )
        self.unit_of_work = PostgresUnitOfWorkAdapter(connection_pool, storage_scope)
        self.queue = JobQueueFacilitator(
            job_repo=self.jobs.job_repo,
            wall_clock=build_fixed_wall_clock(),
            job_wakeup=self.jobs.job_wakeup,
            unit_of_work=self.unit_of_work,
        )

    def store(
        self, stored: InboundEventDocument, queue: JobQueueFacilitatorContract
    ) -> bool:
        return store_and_queue(
            self.events,
            queue,
            stored,
            PROCESS_INBOUND_MESSAGE_JOB,
            None,
            unit_of_work=self.unit_of_work,
        )

    def active_jobs(self, stored: InboundEventDocument) -> set[JobPayloadJson]:
        return self.jobs.job_repo.list_active_payloads(
            PROCESS_INBOUND_MESSAGE_JOB, [encode_inbound_event_payload(stored.id)]
        )


@pytest.fixture
def intake(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
) -> Intake:
    return Intake(connection_pool, postgres_collections, platform_scope)


def test_a_crash_between_storing_and_queuing_leaves_neither(intake: Intake) -> None:
    message = event(BusinessId(), "42")

    with pytest.raises(ExternalServiceError):
        intake.store(message, CrashAfterQueuing(intake.queue))

    # Neither the event nor its job: the webhook failed, and the platform
    # sends it again.
    assert intake.events.get(message.business_id, message.id) is None
    assert intake.active_jobs(message) == set()

    assert intake.store(message, intake.queue) is True
    assert intake.events.get(message.business_id, message.id) is not None
    assert intake.active_jobs(message) == {encode_inbound_event_payload(message.id)}
    # Once more (a redelivery while it waits): stored once, its job again.
    assert intake.store(message, intake.queue) is False


def test_stale_events_are_read_by_status_through_their_index(
    database_url: DatabaseUrl,
    postgres_collections: PostgresCollectionFactory,
    platform_scope: StorageScopeContext,
) -> None:
    events = InboundEventRepository(
        postgres_collections(InboundEventDocument, "inbound_events")
    )
    business_id = BusinessId()
    old, older, fresh = (
        event(business_id, "1", 100 * SECOND),
        event(business_id, "2", 50 * SECOND),
        event(business_id, "3", 900 * SECOND),
    )
    done = event(business_id, "4", 60 * SECOND)
    done.status = InboundEventStatus.ANSWERED
    for stored in (old, older, fresh, done):
        assert events.insert_if_new(stored)

    stale = events.list_stale(
        InboundEventStatus.RECEIVED, Microseconds(500 * SECOND), DocumentQueryLimit(10)
    )
    assert [stored.id for stored in stale] == [older.id, old.id]
    assert [
        stored.id
        for stored in events.list_stale(
            InboundEventStatus.RECEIVED,
            Microseconds(500 * SECOND),
            DocumentQueryLimit(10),
            created_from=Microseconds(60 * SECOND),
        )
    ] == [old.id]

    assert SWEEP_INDEX in sweep_plan_indexes(database_url, platform_scope)


def sweep_plan_indexes(
    database_url: DatabaseUrl, storage_scope: StorageScopeContext
) -> set[str]:
    """The indexes of the plan of the sweeper's read (no sequential scans)."""

    recording_pool = RecordingConnectionPool(database_url)
    try:
        events = InboundEventRepository(
            PostgresCollectionFactory(
                connection_pool=recording_pool,
                storage_scope=storage_scope,
                wall_clock=build_fixed_wall_clock(),
            )(InboundEventDocument, "inbound_events")
        )
        events.list_stale(
            InboundEventStatus.PROCESSING,
            Microseconds(500 * SECOND),
            DocumentQueryLimit(200),
        )
        indexes: set[str] = set()
        with recording_pool.transaction() as connection:
            connection.execute("set local enable_seqscan = off")
            for statement, parameters in recording_pool.transactions[0]:
                # Replays SQL the application composed itself (sql.SQL objects).
                replayed: LiteralString = statement  # pyright: ignore[reportAssignmentType]
                if "set_config" in statement:
                    connection.execute(replayed, parameters or None)
                    continue

                row: TupleRow | None = connection.execute(
                    f"explain (format json) {replayed}", parameters or None
                ).fetchone()
                assert row is not None
                plan = cast(list[dict[str, object]], row[0])[0]["Plan"]
                indexes.update(
                    str(node["Index Name"])
                    for node in plan_nodes(cast(dict[str, object], plan))
                    if node["Node Type"] in INDEX_NODE_TYPES
                )
        return indexes
    finally:
        recording_pool.close()


@pytest.fixture(params=["in_memory", "postgres"])
def stores(request: pytest.FixtureRequest) -> Generator[JobStores]:
    with StorageScopeContext().platform_wide():
        yield job_stores_for(request)


def test_the_queue_tells_which_payloads_still_have_a_job(stores: JobStores) -> None:
    queue = JobQueueFacilitator(
        job_repo=stores.job_repo,
        wall_clock=build_fixed_wall_clock(),
        job_wakeup=stores.job_wakeup,
    )
    waiting, finished, other_job, never = (
        JobPayloadJson(f'{{"event_id": "{name}"}}')
        for name in ("waiting", "finished", "other", "never")
    )
    queue.enqueue(PROCESS_INBOUND_MESSAGE_JOB, waiting, None, lane=JobLane.INBOUND)
    queue.enqueue(JobName("process_post_call"), other_job, None, lane=JobLane.INBOUND)
    done_id = queue.enqueue(
        PROCESS_INBOUND_MESSAGE_JOB, finished, None, lane=JobLane.INBOUND
    )

    def finish(job: QueuedJobDocument) -> None:
        job.status = QueuedJobStatus.DONE

    stores.job_repo.update(done_id, finish)

    assert stores.job_repo.list_active_payloads(
        PROCESS_INBOUND_MESSAGE_JOB, [waiting, finished, other_job, never]
    ) == {waiting}
    assert (
        stores.job_repo.list_active_payloads(PROCESS_INBOUND_MESSAGE_JOB, []) == set()
    )
