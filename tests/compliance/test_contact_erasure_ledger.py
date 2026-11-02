"""
A customer's erasure goes into the ledger outside the database (a queued
job) and is applied again after a restore from a backup taken before it.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.business_closures.bucket_contact_erasure_ledger_adapter import (
    BucketContactErasureLedgerAdapter,
)
from app.adapters.business_closures.bucket_deletion_ledger_mirror_adapter import (
    BucketDeletionLedgerMirrorAdapter,
)
from app.adapters.business_closures.in_memory_contact_erasure_ledger_adapter import (
    InMemoryContactErasureLedgerAdapter,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import JobLane
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.dto.compliance import ContactErasureResult, ContactRecords
from app.schemas.dto.jobs import JobTick, QueuedJobInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.backups.constrained_strings import BackupObjectPrefix
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.compliance.reapply_contact_erasures_use_case import (
    ReapplyContactErasuresUseCase,
)
from app.use_cases.compliance.record_contact_erasure_use_case import (
    RECORD_CONTACT_ERASURE_JOB,
    RecordContactErasureUseCase,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.backups.backup_fakes import InMemoryBackupBucket
from tests.compliance.two_tenants import TwoTenants, command, seed_two_tenants

PREFIX: BackupObjectPrefix = BackupObjectPrefix("workshop/")
TICK: JobTick = JobTick(
    job_name=JobName("reapply_contact_erasures"),
    scheduled_at=Microseconds(1_790_000_000_000_000),
)


def record_of(business_id: BusinessId, erased_at: int = 1) -> ContactErasureRecord:
    return ContactErasureRecord(
        business_id=business_id,
        contact_id=ContactId(),
        erased_at=Microseconds(erased_at),
    )


def reapply(
    tenants: TwoTenants, ledger: InMemoryContactErasureLedgerAdapter
) -> ReapplyContactErasuresUseCase:
    testbed = tenants.testbed
    return ReapplyContactErasuresUseCase(
        ledger=ledger,
        contact_repo=testbed.contact_repo,
        collect_contact_records=testbed.collect_contact_records,
        eraser=testbed.contact_data_eraser,
        audit_log_repo=testbed.audit_log_repo,
        wall_clock=testbed.clock.build_wall_clock(),
        storage_scope=StorageScopeContext(),
    )


def erase_and_record(tenants: TwoTenants) -> InMemoryContactErasureLedgerAdapter:
    """The owner's erasure, and its queued job run into a ledger."""

    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )
    ledger = InMemoryContactErasureLedgerAdapter()
    [job] = tenants.testbed.erasure_ledger_queue.jobs
    RecordContactErasureUseCase(ledger).run(
        QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=job.name,
            payload=job.payload,
            business_id=job.business_id,
        )
    )
    return ledger


def restore_from_before(tenants: TwoTenants) -> None:
    """A backup from before the erasure: the contact and its messages are back."""

    visitor = tenants.visitor
    tenants.testbed.contact_repo.save_many([visitor.contact])
    tenants.testbed.message_repo.save_many(visitor.messages)


def test_an_erasure_queues_its_ledger_record_for_the_batch_worker() -> None:
    tenants = seed_two_tenants()
    tenants.testbed.clock.advance(5)

    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    [job] = tenants.testbed.erasure_ledger_queue.jobs
    assert (job.name, job.business_id, job.lane) == (
        RECORD_CONTACT_ERASURE_JOB,
        tenants.business.id,
        JobLane.DEFAULT,
    )
    assert ContactErasureRecord.model_validate_json(
        str(job.payload)
    ) == ContactErasureRecord(
        business_id=tenants.business.id,
        contact_id=tenants.visitor.contact.id,
        erased_at=tenants.testbed.clock.now_microseconds(),
    )


def test_the_job_refuses_a_record_of_another_business() -> None:
    record = record_of(BusinessId())

    with pytest.raises(ValidationFailedError):
        RecordContactErasureUseCase(InMemoryContactErasureLedgerAdapter()).run(
            QueuedJobInput(
                job_id=QueuedJobId(),
                job_name=RECORD_CONTACT_ERASURE_JOB,
                payload=JobPayloadJson(record.model_dump_json()),
                business_id=BusinessId(),
            )
        )


def test_a_restore_brings_an_erased_customer_back_and_the_job_erases_them() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    visitor = tenants.visitor
    business_id = tenants.business.id
    ledger = erase_and_record(tenants)
    restore_from_before(tenants)
    testbed.clock.advance(60)

    report = reapply(tenants, ledger).run(TICK)

    assert int(report.processed_count) == 1
    erased = testbed.contact_repo.get(business_id, visitor.contact.id)
    assert erased is not None
    assert erased.erased_at == testbed.clock.now_microseconds()
    assert erased.name is None and erased.phone_number is None
    assert (
        testbed.message_repo.list_by_conversation(
            business_id, visitor.chat_conversation.id
        )
        == []
    )
    entry = testbed.audit_log_repo.list_by_business(business_id)[-1]
    assert (entry.action, entry.entity, entry.entity_id, entry.actor_id) == (
        AuditAction.DELETE,
        "contact",
        str(visitor.contact.id),
        None,
    )
    # Erased again, nothing is left to do; the neighbour was never touched.
    assert int(reapply(tenants, ledger).run(TICK).processed_count) == 0
    neighbour = testbed.contact_repo.get(business_id, tenants.neighbour.contact.id)
    assert neighbour is not None and neighbour.erased_at is None


def test_a_still_erased_or_unknown_customer_is_left_alone() -> None:
    tenants = seed_two_tenants()
    ledger = erase_and_record(tenants)
    ledger.record(record_of(tenants.business.id))

    assert int(reapply(tenants, ledger).run(TICK).processed_count) == 0


def test_one_failing_erasure_never_stops_the_others_but_fails_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    ledger = erase_and_record(tenants)
    restore_from_before(tenants)
    neighbour = tenants.neighbour.contact
    ledger.record(
        ContactErasureRecord(
            business_id=tenants.business.id,
            contact_id=neighbour.id,
            erased_at=Microseconds(9),
        )
    )
    erase = testbed.contact_data_eraser.erase

    def failing_for_the_visitor(
        records: ContactRecords, now: Microseconds
    ) -> ContactErasureResult:
        if records.contact.id == tenants.visitor.contact.id:
            raise ExternalServiceError("The recording storage is unavailable.")
        return erase(records, now)

    monkeypatch.setattr(testbed.contact_data_eraser, "erase", failing_for_the_visitor)

    with pytest.raises(ExternalServiceError, match="1 erasures"):
        reapply(tenants, ledger).run(TICK)

    erased = testbed.contact_repo.get(tenants.business.id, neighbour.id)
    assert erased is not None and erased.erased_at is not None


def test_the_bucket_keeps_one_object_per_erased_customer() -> None:
    bucket = InMemoryBackupBucket()
    ledger = BucketContactErasureLedgerAdapter(bucket, PREFIX)
    business_id = BusinessId()
    later, earlier = record_of(business_id, 20), record_of(business_id, 10)

    ledger.record(later)
    ledger.record(earlier)
    ledger.record(later)

    assert sorted(bucket.objects) == sorted(
        f"workshop/deletion-ledger/contacts/{business_id}/{record.contact_id}.erasure"
        for record in (later, earlier)
    )
    assert ledger.read_all() == [earlier, later]
    # The business ledger beside it reads its own records only.
    assert BucketDeletionLedgerMirrorAdapter(bucket, PREFIX).read_all() == []


def test_a_foreign_object_in_the_erasure_ledger_is_refused() -> None:
    bucket = InMemoryBackupBucket()
    bucket.objects[f"workshop/deletion-ledger/contacts/{BusinessId()}/x.erasure"] = (
        b"{}"
    )
    bucket.objects["workshop/deletion-ledger/contacts/notes.txt"] = b"ignored"

    with pytest.raises(ExternalServiceError, match="not an erasure record"):
        BucketContactErasureLedgerAdapter(bucket, PREFIX).read_all()


def test_the_in_memory_ledger_keeps_the_first_record() -> None:
    ledger = InMemoryContactErasureLedgerAdapter()
    first = record_of(BusinessId(), 5)

    ledger.record(first)
    ledger.record(first.model_copy(update={"erased_at": Microseconds(9)}))

    assert ledger.read_all() == [first]
