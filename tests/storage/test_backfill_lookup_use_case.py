"""The lookup backfill use case with a fake adapter (no database)."""

import pytest

from app.contracts.storage import LookupColumnBackfillAdapterContract
from app.schemas.dto.lookup_backfill import (
    BackfillLookupColumnsCommand,
    LookupBackfillBatch,
    LookupBackfillReport,
    TriggerLookupColumn,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    LookupBackfillBatchSize,
    MigrationAttemptLimit,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.use_cases.maintenance.backfill_lookup_columns_use_case import (
    BackfillLookupColumnsUseCase,
)
from tests.storage.storage_testing import RecordedRetryPause


def column(collection: str, field: str) -> TriggerLookupColumn:
    return TriggerLookupColumn(
        collection_name=DocumentCollectionName(collection),
        field=DocumentFieldPath(field),
    )


class FakeBackfill(LookupColumnBackfillAdapterContract):
    """Ten sorted keys per table, every odd one missing its value."""

    def __init__(self, lock_timeouts: int = 0) -> None:
        self.columns: list[TriggerLookupColumn] = [
            column("contacts", "display_name_folded"),
            column("contacts", "last_seen_at"),
            column("knowledge_items", "updated_at"),
        ]
        self.keys: list[str] = [f"k{index}" for index in range(10)]
        self.calls: list[tuple[str, str | None, int]] = []
        self._lock_timeouts: int = lock_timeouts

    def list_trigger_columns(self) -> list[TriggerLookupColumn]:
        return list(self.columns)

    def count_missing(self, column: TriggerLookupColumn) -> DocumentCount:
        return DocumentCount(5)

    def fill_batch(
        self,
        column: TriggerLookupColumn,
        after: StoredDocumentKey | None,
        batch_size: LookupBackfillBatchSize,
    ) -> LookupBackfillBatch:
        self.calls.append(
            (str(column.field), None if after is None else str(after), int(batch_size))
        )
        if self._lock_timeouts > 0:
            self._lock_timeouts -= 1
            raise MigrationLockTimeoutError("row locked")

        batch = [key for key in self.keys if after is None or key > str(after)]
        batch = batch[: int(batch_size)]
        return LookupBackfillBatch(
            last_document_key=StoredDocumentKey(batch[-1]) if batch else None,
            scanned_count=DocumentCount(len(batch)),
            filled_count=DocumentCount(sum(1 for key in batch if int(key[1:]) % 2)),
        )


def run(
    backfill: FakeBackfill,
    command: BackfillLookupColumnsCommand,
    pause: RecordedRetryPause | None = None,
    attempt_limit: int = 5,
) -> LookupBackfillReport:
    return BackfillLookupColumnsUseCase(
        backfill=backfill,
        retry_pause=pause or RecordedRetryPause(),
        attempt_limit=MigrationAttemptLimit(attempt_limit),
    ).run(command)


def test_one_column_is_walked_in_keyset_batches_to_the_end() -> None:
    backfill = FakeBackfill()

    report = run(
        backfill,
        BackfillLookupColumnsCommand(
            collection_name=DocumentCollectionName("contacts"),
            field=DocumentFieldPath("last_seen_at"),
            batch_size=LookupBackfillBatchSize(4),
        ),
    )

    assert backfill.calls == [
        ("last_seen_at", None, 4),
        ("last_seen_at", "k3", 4),
        ("last_seen_at", "k7", 4),
    ]
    [entry] = report.columns
    assert (int(entry.scanned), int(entry.filled), int(entry.batch_count)) == (10, 5, 3)


def test_without_names_every_trigger_column_is_backfilled() -> None:
    report = run(FakeBackfill(), BackfillLookupColumnsCommand())

    assert [f"{e.collection_name}.{e.field}" for e in report.columns] == [
        "contacts.display_name_folded",
        "contacts.last_seen_at",
        "knowledge_items.updated_at",
    ]


def test_a_dry_run_only_counts() -> None:
    backfill = FakeBackfill()

    report = run(
        backfill,
        BackfillLookupColumnsCommand(
            collection_name=DocumentCollectionName("contacts"), is_dry_run=True
        ),
    )

    assert report.is_dry_run
    assert [int(entry.missing) for entry in report.columns] == [5, 5]
    assert backfill.calls == []


def test_an_unknown_column_is_refused_before_anything_runs() -> None:
    backfill = FakeBackfill()

    with pytest.raises(NotFoundError, match="contacts.phone_number"):
        run(
            backfill,
            BackfillLookupColumnsCommand(
                collection_name=DocumentCollectionName("contacts"),
                field=DocumentFieldPath("phone_number"),
            ),
        )

    assert backfill.calls == []


def test_a_field_needs_its_collection() -> None:
    with pytest.raises(ValueError, match="together with its collection"):
        BackfillLookupColumnsCommand(field=DocumentFieldPath("last_seen_at"))


def test_a_locked_batch_is_tried_again_then_given_up() -> None:
    pause = RecordedRetryPause()
    command = BackfillLookupColumnsCommand(
        collection_name=DocumentCollectionName("knowledge_items")
    )

    report = run(FakeBackfill(lock_timeouts=2), command, pause)

    assert pause.attempts == [1, 2]
    assert [int(entry.filled) for entry in report.columns] == [5]
    with pytest.raises(ExternalServiceError, match="gave up after 3 tries"):
        run(FakeBackfill(lock_timeouts=9), command, attempt_limit=3)
