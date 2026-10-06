"""
Shared pieces of the data-task tests: the stored state over an in-memory
collection, registries of a chosen set of tasks, worker pulses.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.maintenance.data_task_registry import DataTaskRegistry
from app.repositories.data_task_state_repository import DataTaskStateRepository
from app.schemas.constants.maintenance import IndexedList
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.data_tasks import LookupBackfillDeclaration
from app.schemas.typings.platform.constrained_strings import (
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
    SchemaMigrationName,
)
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

SECOND: int = 1_000_000
MINUTE: int = 60 * SECOND
HOUR: int = 60 * MINUTE
# 2026-10-06T12:00:00Z
NOW: int = 1_791_288_000 * SECOND
RELEASE: ReleaseVersion = ReleaseVersion("release-new")
OLD_RELEASE: ReleaseVersion = ReleaseVersion("release-old")


def data_task_states() -> DataTaskStateRepository:
    return DataTaskStateRepository(
        InMemoryDocumentCollectionAdapter[DataTaskStateDocument](DataTaskStateDocument)
    )


def no_data_tasks() -> DataTaskRegistry:
    """A registry without tasks: nothing is ever open."""

    return DataTaskRegistry(collections=(), backfills=())


def backfill_of(
    collection: str, field: str, *lists: IndexedList
) -> LookupBackfillDeclaration:
    return LookupBackfillDeclaration(
        collection_name=DocumentCollectionName(collection),
        field=DocumentFieldPath(field),
        migration=SchemaMigrationName("1122_online_lookup_columns"),
        lists=list(lists),
    )


def registry_of(
    collections: Sequence[DocumentCollectionDefinition] = (),
    backfills: Sequence[LookupBackfillDeclaration] = (),
) -> DataTaskRegistry:
    return DataTaskRegistry(collections=collections, backfills=backfills)


def pulse(
    release: ReleaseVersion | None, beat_at: int, host: str = "worker-1"
) -> WorkerHeartbeatDocument:
    return WorkerHeartbeatDocument(
        host_name=WorkerHostName(host),
        release=release,
        started_at=Microseconds(beat_at - HOUR),
        beat_at=Microseconds(beat_at),
        created_at=Microseconds(beat_at - HOUR),
        updated_at=Microseconds(beat_at),
    )
