"""The platform admin's data-task card and the retry of a failed task."""

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.maintenance import DataTaskStatus, IndexedList
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.admin_system import TableSizeView
from app.schemas.dto.data_tasks import DataTasksQuery, RetryDataTaskCommand
from app.schemas.dto.platform_health import DatabaseSize
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.backups.constrained_strings import DatabaseTableName
from app.schemas.typings.maintenance.constrained_integers import DataTaskBatchSize
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.monitoring.constrained_integers import (
    CollectionRowEstimate,
    StorageByteSize,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.system.get_data_tasks_use_case import GetDataTasksUseCase
from app.use_cases.admin.system.retry_data_task_use_case import (
    RetryDataTaskUseCase,
)
from app.utilities.maintenance.data_task_progress import new_state
from tests.data_tasks.data_task_support import (
    HOUR,
    MINUTE,
    NOW,
    OLD_RELEASE,
    RELEASE,
    backfill_of,
    data_task_states,
    pulse,
    registry_of,
)
from tests.data_tasks.runner_world import Pulses
from tests.platform_ops.ops_world import ADMIN, AdminsOnly, OpsClock

SEEN: DataTaskKey = DataTaskKey("backfill_lookup:contacts.last_seen_at")
UPDATED: DataTaskKey = DataTaskKey("backfill_lookup:knowledge_items.updated_at")
SOURCES: DataTaskKey = DataTaskKey("backfill_lookup:bookings.source_channel")


class Catalog:
    def __init__(self, fails: bool = False) -> None:
        self.fails: bool = fails

    def measure(self) -> DatabaseSize | None:
        if self.fails:
            raise ExternalServiceError("pg_class is not readable.")
        return DatabaseSize(
            total_bytes=StorageByteSize(1_000),
            tables=[
                TableSizeView(
                    table=DatabaseTableName("workshop.contacts"),
                    total_bytes=StorageByteSize(1_000),
                    row_estimate=CollectionRowEstimate(48_000),
                )
            ],
        )


class Card:
    def __init__(self, catalog_fails: bool = False) -> None:
        self.clock = OpsClock(Microseconds(NOW))
        self.registry = registry_of(
            backfills=[
                backfill_of("contacts", "last_seen_at", IndexedList.CUSTOMERS),
                backfill_of("knowledge_items", "updated_at", IndexedList.KNOWLEDGE),
                backfill_of("bookings", "source_channel"),
            ]
        )
        self.states = data_task_states()
        self.pulses = Pulses()
        self.audit = InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
            AuditLogEntryDocument
        )
        self.view = GetDataTasksUseCase(
            authorize_platform_admin=AdminsOnly(),
            registry=self.registry,
            state_repo=self.states,
            pulse_repo=self.pulses,
            database_size=Catalog(catalog_fails),
            wall_clock=self.clock.wall_clock,
            release=RELEASE,
            batch_size=DataTaskBatchSize(5_000),
        )
        self.retry = RetryDataTaskUseCase(
            authorize_platform_admin=AdminsOnly(),
            registry=self.registry,
            state_repo=self.states,
            audit_log_repo=AuditLogRepository(self.audit),
            wall_clock=self.clock.wall_clock,
        )

    def store(self, key: DataTaskKey, status: DataTaskStatus, since: int) -> None:
        task = self.registry.find_task(key)
        assert task is not None
        self.states.save(
            new_state(task, Microseconds(since)).model_copy(update={"status": status})
        )


def test_the_card_lists_open_tasks_first_with_counts_and_the_overlap() -> None:
    card = Card()
    card.store(SEEN, DataTaskStatus.RUNNING, NOW - 30 * HOUR)
    card.store(UPDATED, DataTaskStatus.DONE, NOW - HOUR)
    card.pulses.pulses.append(pulse(OLD_RELEASE, NOW - 2 * MINUTE))

    view = card.view.run(DataTasksQuery(user_id=ADMIN))

    assert [str(task.key) for task in view.tasks] == [
        str(SEEN),
        str(SOURCES),
        str(UPDATED),
    ]
    assert (int(view.open_count), int(view.failed_count), int(view.stalled_count)) == (
        2,
        0,
        1,
    )
    seen, sources, updated = view.tasks
    assert seen.is_stalled and seen.row_estimate == CollectionRowEstimate(48_000)
    assert sources.status is DataTaskStatus.PENDING and sources.pending_since is None
    assert updated.pending_since is None, "A done task is not due."
    assert int(view.batch_size) == 5_000
    assert not view.rollout.is_settled
    assert view.rollout.other_releases == [OLD_RELEASE]


def test_the_card_shows_without_table_sizes_when_the_catalog_fails() -> None:
    view = Card(catalog_fails=True).view.run(DataTasksQuery(user_id=ADMIN))

    assert all(task.row_estimate is None for task in view.tasks)
    assert view.rollout.is_settled


def test_only_platform_admins_see_or_retry_tasks() -> None:
    card = Card()

    with pytest.raises(AccessDeniedError):
        card.view.run(DataTasksQuery(user_id=UserId()))
    with pytest.raises(AccessDeniedError):
        card.retry.run(RetryDataTaskCommand(user_id=UserId(), key=SEEN))


def test_a_failed_task_is_walked_again_and_the_retry_is_audited() -> None:
    card = Card()
    card.store(SEEN, DataTaskStatus.FAILED, NOW - 30 * HOUR)

    result = card.retry.run(RetryDataTaskCommand(user_id=ADMIN, key=SEEN))

    state = card.states.get_many([SEEN])[0]
    assert state.status is DataTaskStatus.PENDING
    assert int(state.pending_since) == NOW - 30 * HOUR
    assert result.task.status is DataTaskStatus.PENDING
    [entry] = card.audit.list_all()
    assert entry.id == result.audit_log_entry_id
    assert (entry.action, str(entry.entity), str(entry.entity_id)) == (
        AuditAction.UPDATE,
        "data_task",
        str(SEEN),
    )
    assert entry.actor_id == ADMIN


def test_only_a_failed_task_can_be_retried() -> None:
    card = Card()
    card.store(UPDATED, DataTaskStatus.DONE, NOW - HOUR)

    with pytest.raises(ConflictError):
        card.retry.run(RetryDataTaskCommand(user_id=ADMIN, key=UPDATED))
    with pytest.raises(ConflictError):
        card.retry.run(RetryDataTaskCommand(user_id=ADMIN, key=SOURCES))
    with pytest.raises(NotFoundError):
        card.retry.run(
            RetryDataTaskCommand(
                user_id=ADMIN, key=DataTaskKey("backfill_lookup:contacts.nickname")
            )
        )
    assert card.audit.list_all() == []
