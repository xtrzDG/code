"""The ledger's fingerprint and its copies outside the database."""

import pytest
from typed_time_provider import Microseconds

from app.adapters.business_closures.bucket_deletion_ledger_mirror_adapter import (
    BucketDeletionLedgerMirrorAdapter,
)
from app.adapters.business_closures.in_memory_deletion_ledger_mirror_adapter import (
    InMemoryDeletionLedgerMirrorAdapter,
)
from app.schemas.domain.business_closures import (
    BusinessDeletionDocument,
    CollectionRowCount,
)
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.backups.constrained_strings import BackupObjectPrefix
from app.schemas.typings.business_closures.constrained_integers import (
    DeletedRowCount,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.business_closures.certificate_digest import certificate_digest
from app.utilities.business_closures.closure_identity import deletion_id_for
from tests.backups.backup_fakes import InMemoryBackupBucket
from tests.storage.document_evolution.sample_documents import sample_document

PREFIX: BackupObjectPrefix = BackupObjectPrefix("workshop/")


def record(business_id: BusinessId, started_at: int) -> DeletionLedgerRecord:
    return DeletionLedgerRecord(
        business_id=business_id,
        deletion_id=deletion_id_for(business_id),
        started_at=Microseconds(started_at),
    )


def test_the_fingerprint_follows_the_certified_facts_only() -> None:
    entry = sample_document(
        BusinessDeletionDocument, DocumentCollectionName("business_deletions")
    )
    more_rows = entry.model_copy(
        update={
            "erased_rows": [
                CollectionRowCount(
                    collection=DocumentCollectionName("contacts"),
                    row_count=DeletedRowCount(7),
                )
            ]
        }
    )
    touched = entry.model_copy(update={"updated_at": Microseconds(1)})

    assert certificate_digest(entry) == certificate_digest(touched)
    assert certificate_digest(entry) != certificate_digest(more_rows)


def test_the_bucket_keeps_one_record_per_business_outside_the_backups() -> None:
    bucket = InMemoryBackupBucket()
    mirror = BucketDeletionLedgerMirrorAdapter(bucket, PREFIX)
    first, second = BusinessId(), BusinessId()

    mirror.record(record(second, 20))
    mirror.record(record(first, 10))
    mirror.record(record(first, 10))

    assert [item.business_id for item in mirror.read_all()] == [first, second]
    assert all(key.startswith("workshop/deletion-ledger/") for key in bucket.objects)
    assert len(bucket.objects) == 2


def test_a_foreign_object_in_the_ledger_folder_is_reported() -> None:
    bucket = InMemoryBackupBucket()
    bucket.objects["workshop/deletion-ledger/notes.txt"] = b"not a record"
    bucket.objects["workshop/deletion-ledger/broken.json"] = b"{}"
    mirror = BucketDeletionLedgerMirrorAdapter(bucket, PREFIX)

    with pytest.raises(ExternalServiceError):
        mirror.read_all()


def test_the_process_mirror_keeps_the_first_record_of_a_business() -> None:
    mirror = InMemoryDeletionLedgerMirrorAdapter()
    business = BusinessId()

    mirror.record(record(business, 30))
    mirror.record(record(business, 40))

    assert [int(item.started_at) for item in mirror.read_all()] == [30]
