"""The data-task registry: one task per migrated collection and per backfill."""

from app.adapters.storage.document_upgrades import declared_schema_version
from app.registries.maintenance.data_task_registry import (
    DataTaskRegistry,
    backfill_task_key,
    migration_task_key,
)
from app.registries.maintenance.lookup_backfills import LOOKUP_BACKFILLS
from app.schemas.constants.maintenance import DataTaskKind, IndexedList
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import DataTaskDefinition
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from tests.data_tasks.data_task_support import backfill_of, registry_of


def test_every_collection_above_version_one_has_a_migration_task() -> None:
    registry = DataTaskRegistry()
    migrations: dict[str, DataTaskDefinition] = {
        str(task.collection_name): task
        for task in registry.list_tasks()
        if task.kind is DataTaskKind.MIGRATE_DOCUMENTS
    }
    expected: dict[str, DocumentSchemaVersionNumber] = {}
    for definition in DOCUMENT_COLLECTIONS:
        version = declared_schema_version(definition.document_type)
        if version is not None and int(version) > 1:
            expected[str(definition.name)] = version

    assert {name: task.target_version for name, task in migrations.items()} == (
        expected
    )
    assert "contacts" in migrations
    assert migrations["contacts"].lists == [IndexedList.CUSTOMERS]
    assert migrations["knowledge_items"].lists == [IndexedList.KNOWLEDGE]


def test_every_declared_backfill_is_a_task_after_the_migrations() -> None:
    tasks: list[DataTaskDefinition] = DataTaskRegistry().list_tasks()
    kinds: list[DataTaskKind] = [task.kind for task in tasks]
    backfills = [task for task in tasks if task.kind is DataTaskKind.BACKFILL_LOOKUP]

    assert kinds == sorted(
        kinds, key=lambda kind: kind is DataTaskKind.BACKFILL_LOOKUP
    ), "Document migrations run before the backfills."
    assert [(task.collection_name, task.field) for task in backfills] == [
        (item.collection_name, item.field) for item in LOOKUP_BACKFILLS
    ]
    assert len({task.key for task in tasks}) == len(tasks)


def test_keys_name_the_collection_and_the_field() -> None:
    assert migration_task_key(DocumentCollectionName("contacts")) == DataTaskKey(
        "migrate_documents:contacts"
    )
    assert backfill_task_key(
        DocumentCollectionName("contacts"), DocumentFieldPath("last_seen_at")
    ) == DataTaskKey("backfill_lookup:contacts.last_seen_at")


def test_a_registry_finds_its_tasks_by_key_and_by_list() -> None:
    registry = registry_of(
        collections=[
            DocumentCollectionDefinition(
                name=DocumentCollectionName("contacts"), document_type=ContactDocument
            ),
            # Version 1: nothing older to rewrite.
            DocumentCollectionDefinition(
                name=DocumentCollectionName("data_task_states"),
                document_type=DataTaskStateDocument,
            ),
        ],
        backfills=[
            backfill_of("contacts", "last_seen_at", IndexedList.CUSTOMERS),
            backfill_of("knowledge_items", "updated_at", IndexedList.KNOWLEDGE),
        ],
    )

    assert [str(task.key) for task in registry.list_tasks()] == [
        "migrate_documents:contacts",
        "backfill_lookup:contacts.last_seen_at",
        "backfill_lookup:knowledge_items.updated_at",
    ]
    assert registry.find_task(DataTaskKey("backfill_lookup:contacts.last_seen_at"))
    assert registry.find_task(DataTaskKey("backfill_lookup:contacts.created_at")) is (
        None
    )
    assert [
        str(task.key) for task in registry.tasks_for_list(IndexedList.KNOWLEDGE)
    ] == ["backfill_lookup:knowledge_items.updated_at"]
    # The contacts migration holds the customer list back too.
    assert [
        str(task.key) for task in registry.tasks_for_list(IndexedList.CUSTOMERS)
    ] == [
        "migrate_documents:contacts",
        "backfill_lookup:contacts.last_seen_at",
    ]
