from collections.abc import Mapping, Sequence

from app.adapters.storage.document_upgrades import declared_schema_version
from app.contracts.data_tasks import DataTaskRegistryContract
from app.registries.maintenance.lookup_backfills import (
    LOOKUP_BACKFILLS,
    MIGRATION_LISTS,
)
from app.schemas.constants.maintenance import DataTaskKind, IndexedList
from app.schemas.dto.data_tasks import DataTaskDefinition, LookupBackfillDeclaration
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

FIRST_VERSION: int = 1


class DataTaskRegistry(DataTaskRegistryContract):
    """
    The post-deploy data tasks of this release (the `data_tasks` registry):

    - one document migration per collection whose document type has a
      `schema_version` above 1, to that version: rows of an older shape
      are rewritten after the release (`workshop migrate-documents`), and
      a later version bump makes it pending again;
    - one backfill per trigger-kept lookup column added to a table that
      already held rows (`lookup_backfills.py`, `workshop backfill-lookup`).

    Migrations come first: a rewritten row runs the lookup trigger, so the
    backfills afterwards find little left to fill.
    """

    def __init__(
        self,
        collections: Sequence[DocumentCollectionDefinition] = DOCUMENT_COLLECTIONS,
        backfills: Sequence[LookupBackfillDeclaration] = LOOKUP_BACKFILLS,
        migration_lists: Mapping[
            DocumentCollectionName, tuple[IndexedList, ...]
        ] = MIGRATION_LISTS,
    ) -> None:
        self._tasks: tuple[DataTaskDefinition, ...] = (
            *migration_tasks(collections, migration_lists),
            *(backfill_task(declaration) for declaration in backfills),
        )
        self._by_key: dict[DataTaskKey, DataTaskDefinition] = {
            task.key: task for task in self._tasks
        }

    def list_tasks(self) -> list[DataTaskDefinition]:
        return list(self._tasks)

    def find_task(self, key: DataTaskKey) -> DataTaskDefinition | None:
        return self._by_key.get(key)

    def tasks_for_list(self, indexed_list: IndexedList) -> list[DataTaskDefinition]:
        return [task for task in self._tasks if indexed_list in task.lists]


def migration_task_key(collection_name: DocumentCollectionName) -> DataTaskKey:
    return DataTaskKey(f"{DataTaskKind.MIGRATE_DOCUMENTS.value}:{collection_name}")


def backfill_task_key(
    collection_name: DocumentCollectionName, field: DocumentFieldPath
) -> DataTaskKey:
    return DataTaskKey(
        f"{DataTaskKind.BACKFILL_LOOKUP.value}:{collection_name}.{field}"
    )


def migration_tasks(
    collections: Sequence[DocumentCollectionDefinition],
    migration_lists: Mapping[DocumentCollectionName, tuple[IndexedList, ...]],
) -> list[DataTaskDefinition]:
    tasks: list[DataTaskDefinition] = []
    for definition in collections:
        version: DocumentSchemaVersionNumber | None = declared_schema_version(
            definition.document_type
        )
        if version is None or int(version) <= FIRST_VERSION:
            continue

        tasks.append(
            DataTaskDefinition(
                key=migration_task_key(definition.name),
                kind=DataTaskKind.MIGRATE_DOCUMENTS,
                collection_name=definition.name,
                target_version=version,
                lists=list(migration_lists.get(definition.name, ())),
            )
        )

    return tasks


def backfill_task(declaration: LookupBackfillDeclaration) -> DataTaskDefinition:
    return DataTaskDefinition(
        key=backfill_task_key(declaration.collection_name, declaration.field),
        kind=DataTaskKind.BACKFILL_LOOKUP,
        collection_name=declaration.collection_name,
        field=declaration.field,
        lists=list(declaration.lists),
    )
