"""
The drill hands both ledgers outside the database to the restored
database: the deleted businesses (deleted again) and the erased customers
(counted), and its report says what each found.
"""

from pathlib import Path

import pytest

from app.adapters.backup.age_backup_cipher_adapter import AgeBackupCipherAdapter
from app.adapters.business_closures.in_memory_contact_erasure_ledger_adapter import (
    InMemoryContactErasureLedgerAdapter,
)
from app.adapters.business_closures.in_memory_deletion_ledger_mirror_adapter import (
    InMemoryDeletionLedgerMirrorAdapter,
)
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.gateways.cli.restore_check import describe_drill
from app.schemas.dto.backups import DeletionLedgerApplication
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.schemas.typings.business_closures.constrained_integers import (
    DeletedRowCount,
    ErasedContactCount,
    LedgerBusinessCount,
    RestoredContactCount,
    ResurrectedRowCount,
)
from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.maintenance.backups.check_backup_restore_use_case import (
    CheckBackupRestoreUseCase,
)
from tests.backups.backup_fakes import (
    PREFIX,
    FakeScratchDatabase,
    InMemoryBackupBucket,
    clock_at,
)
from tests.backups.test_backup_use_cases import (
    IDENTITY,
    MIGRATION_SQL,
    command,
    facts,
    take_backup,
)


@pytest.fixture
def work(tmp_path: Path) -> Path:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_document_collections.sql").write_text(MIGRATION_SQL)
    return tmp_path


def test_the_drill_hands_both_ledgers_to_the_restored_database(work: Path) -> None:
    bucket = InMemoryBackupBucket()
    take_backup(bucket, work, "2026-10-03T01:07:00")
    scratch = FakeScratchDatabase(facts())
    deletions = InMemoryDeletionLedgerMirrorAdapter()
    deleted = DeletionLedgerRecord(
        business_id=BusinessId(), deletion_id=BusinessDeletionId(), started_at=1
    )
    deletions.record(deleted)
    erasures = InMemoryContactErasureLedgerAdapter()
    erased = ContactErasureRecord(
        business_id=BusinessId(), contact_id=ContactId(), erased_at=2
    )
    erasures.record(erased)

    report = CheckBackupRestoreUseCase(
        backup_bucket=bucket,
        backup_cipher=AgeBackupCipherAdapter([], IDENTITY),
        scratch_database=scratch,
        migration_source=SqlFileMigrationSourceAdapter(work / "migrations"),
        wall_clock=clock_at("2026-10-03T02:00:00"),
        prefix=PREFIX,
        max_age=BackupFreshnessHours(26),
        ledger_mirror=deletions,
        contact_erasure_ledger=erasures,
    ).run(command(work))

    assert report.problems == []
    assert scratch.ledgers == [[deleted.business_id]]
    assert scratch.erasure_ledgers == [[erased]]


def test_the_report_counts_the_erased_customers_a_backup_brings_back(
    work: Path,
) -> None:
    bucket = InMemoryBackupBucket()
    take_backup(bucket, work, "2026-10-03T01:07:00")
    report = CheckBackupRestoreUseCase(
        backup_bucket=bucket,
        backup_cipher=AgeBackupCipherAdapter([], IDENTITY),
        scratch_database=FakeScratchDatabase(facts()),
        migration_source=SqlFileMigrationSourceAdapter(work / "migrations"),
        wall_clock=clock_at("2026-10-03T02:00:00"),
        prefix=PREFIX,
        max_age=BackupFreshnessHours(26),
    ).run(command(work))
    restored = report.restored.model_copy(
        update={
            "ledger": DeletionLedgerApplication(
                deleted_businesses=LedgerBusinessCount(1),
                erased_rows=DeletedRowCount(4),
                remaining_rows=ResurrectedRowCount(0),
                erased_contacts=ErasedContactCount(3),
                restored_contacts=RestoredContactCount(2),
            )
        }
    )

    text = describe_drill(report.model_copy(update={"restored": restored}), False)

    assert "Erasure ledger: 3 erased customers, 2 of them with their data" in text
    assert "reapply_contact_erasures" in text
