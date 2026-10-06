"""
The post-deploy data tasks on Postgres: a lookup column like migration
1122's fills by itself after the deploy and the list that pages by it comes
out complete; a document migration walks its table in keyset batches.
"""

from typed_time_provider import Microseconds

from app.adapters.locks.postgres_advisory_lock_adapter import (
    PostgresAdvisoryLockAdapter,
)
from app.adapters.storage.persisted_document_codec import parse_stored_object
from app.adapters.storage.postgres.postgres_data_task_batch_adapter import (
    PostgresDataTaskBatchAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.registries.locks.data_task_lock_registry import DataTaskLockRegistry
from app.registries.maintenance.data_task_registry import DataTaskRegistry
from app.repositories.data_task_state_repository import DataTaskStateRepository
from app.repositories.knowledge_repositories import KnowledgeItemRepository
from app.schemas.constants.maintenance import (
    DataTaskKind,
    DataTaskStatus,
    IndexedList,
)
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.data_tasks import (
    DataTaskBatchRequest,
    DataTaskBatchResult,
    DataTaskDefinition,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.maintenance.constrained_integers import DataTaskBatchSize
from app.schemas.typings.maintenance.constrained_strings import (
    DataTaskKey,
    DataTaskPosition,
)
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.use_cases.maintenance.data_tasks.run_data_tasks_use_case import (
    RunDataTasksUseCase,
)
from app.use_cases.shared.list_indexing import read_list_indexing
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.data_tasks.runner_world import Pulses
from tests.storage.builders import COUNTRY_SAMPLES, build_knowledge_item
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.evolution_documents import (
    NOTE_UPCASTERS,
    NOTES_COLLECTION,
    NoteV2,
    build_note_v1,
)
from tests.storage.storage_testing import build_fixed_wall_clock
from tests.storage.stored_rows import read_stored, write_stored

BUSINESS: BusinessId = BusinessId()
TICK: JobTick = JobTick(
    job_name=JobName("run_data_tasks"), scheduled_at=Microseconds(1)
)


def seed_knowledge(
    collections: PostgresCollectionFactory, scope: StorageScopeContext
) -> list[KnowledgeItemDocument]:
    """Twelve items, each changed a minute after the one before."""

    repo = KnowledgeItemRepository(
        collections(KnowledgeItemDocument, "knowledge_items")
    )
    items: list[KnowledgeItemDocument] = []
    with scope.scoped_to_business(BUSINESS):
        for index in range(12):
            item = build_knowledge_item(COUNTRY_SAMPLES[0], BUSINESS).model_copy(
                update={"updated_at": Microseconds(1_000_000 + index * 60_000_000)}
            )
            repo.save(item)
            items.append(item)
    return items


def forget_lookups(connection_pool: PostgresConnectionPoolClient) -> None:
    """The rows as a release before 1122 left them: the columns are empty."""

    with connection_pool.transaction() as connection:
        connection.execute("select set_config('app.bypass_rls', 'on', true)")
        connection.execute(
            "update workshop.knowledge_items "
            "set doc_updated_at = null, doc_is_active = null"
        )


def knowledge_page(
    collections: PostgresCollectionFactory, scope: StorageScopeContext
) -> list[str]:
    repo = KnowledgeItemRepository(
        collections(KnowledgeItemDocument, "knowledge_items")
    )
    with scope.scoped_to_business(BUSINESS):
        page = repo.page_by_business(
            BUSINESS, KeysetSlice(limit=KeysetReadLimit(50)), None, None
        )
    return [str(item.id) for item in page]


def test_a_lookup_column_fills_after_the_deploy_and_the_list_is_complete(
    connection_pool: PostgresConnectionPoolClient,
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    items = seed_knowledge(postgres_collections, storage_scope)
    forget_lookups(connection_pool)
    states = DataTaskStateRepository(
        postgres_collections(DataTaskStateDocument, "data_task_states")
    )
    registry = DataTaskRegistry()
    runner = RunDataTasksUseCase(
        registry=registry,
        state_repo=states,
        batches=PostgresDataTaskBatchAdapter(connection_pool),
        locks=DataTaskLockRegistry(
            PostgresAdvisoryLockAdapter(
                connection_pool,
                PostgresUnitOfWorkAdapter(connection_pool, storage_scope),
            )
        ),
        pulse_repo=Pulses(),
        wall_clock=build_fixed_wall_clock(),
        release=None,
        batch_size=DataTaskBatchSize(100),
    )
    newest_first: list[str] = [str(item.id) for item in reversed(items)]

    before: list[str] = knowledge_page(postgres_collections, storage_scope)
    with storage_scope.scoped_to_business(BUSINESS):
        indexing_before = read_list_indexing(registry, states, IndexedList.KNOWLEDGE)
    runner.run(TICK)
    after: list[str] = knowledge_page(postgres_collections, storage_scope)
    with storage_scope.scoped_to_business(BUSINESS):
        indexing_after = read_list_indexing(registry, states, IndexedList.KNOWLEDGE)
        stored = states.get_many(
            [task.key for task in registry.tasks_for_list(IndexedList.KNOWLEDGE)]
        )

    assert before != newest_first, "Before the backfill the list is not right."
    assert after == newest_first
    assert indexing_before is True and indexing_after is False
    assert {state.status for state in stored} == {DataTaskStatus.DONE}
    updated = next(s for s in stored if str(s.key).endswith(".updated_at"))
    assert int(updated.scanned_count) == 12 and int(updated.batch_count) == 1


def walk(
    adapter: PostgresDataTaskBatchAdapter, task: DataTaskDefinition
) -> list[DataTaskBatchResult]:
    results: list[DataTaskBatchResult] = []
    after: DataTaskPosition | None = None
    while True:
        result = adapter.run_batch(
            DataTaskBatchRequest(
                task=task, after=after, batch_size=DataTaskBatchSize(100)
            )
        )
        results.append(result)
        if result.next_position is None:
            return results
        after = result.next_position
        assert len(results) < 10


def test_a_document_migration_rewrites_old_rows_in_keyset_batches(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    keys: list[str] = []
    for position in range(150):
        note = build_note_v1(BUSINESS)
        keys.append(str(note.id))
        stored = parse_stored_object(note.model_dump_json())
        if position == 120:
            del stored["title"]
        write_stored(connection_pool, keys[-1], BUSINESS, stored, written_at=position)
    adapter = PostgresDataTaskBatchAdapter(
        connection_pool,
        collections=[DocumentCollectionDefinition(NOTES_COLLECTION, NoteV2)],
        upcasters={NOTES_COLLECTION: NOTE_UPCASTERS},
    )
    task = DataTaskDefinition(
        key=DataTaskKey("migrate_documents:knowledge_items"),
        kind=DataTaskKind.MIGRATE_DOCUMENTS,
        collection_name=NOTES_COLLECTION,
        target_version=DocumentSchemaVersionNumber(2),
    )

    first = walk(adapter, task)
    again = walk(adapter, task)

    assert [int(result.scanned) for result in first] == [100, 50]
    assert sum(int(result.changed) for result in first) == 149
    assert [str(key) for r in first for key in r.failed_document_keys] == [keys[120]]
    assert read_stored(connection_pool, keys[0])["schema_version"] == "2"
    assert read_stored(connection_pool, keys[120])["schema_version"] == "1"
    assert sum(int(result.changed) for result in again) == 0
