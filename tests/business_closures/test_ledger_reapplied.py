"""
The deletion ledger applied again after a restore (the daily job): a
deleted business whose rows came back with a restored backup loses them
again, in every table but what the law keeps; a deletion still under way
is left to its own job, and a business the ledger does not name is never
touched.
"""

from typed_time_provider import Microseconds

from app.adapters.business_closures.in_memory_deletion_ledger_mirror_adapter import (
    InMemoryDeletionLedgerMirrorAdapter,
)
from app.adapters.storage.in_memory_business_row_eraser_adapter import (
    InMemoryBusinessRowEraserAdapter,
)
from app.adapters.storage.in_memory_collection_registry import (
    InMemoryCollectionRegistry,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_closure_repositories import BusinessDeletionRepository
from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.businesses.deletion.reapply_deletion_ledger_use_case import (
    ReapplyDeletionLedgerUseCase,
)
from app.utilities.business_closures.closure_identity import deletion_id_for
from tests.business_closures.closure_world import DAY_SECONDS, open_closure_world
from tests.storage.builders import COUNTRY_SAMPLES, build_contact
from tests.storage.document_evolution.sample_documents import sample_document

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
TICK: JobTick = JobTick(job_name=JobName("reapply_deletion_ledger"), scheduled_at=NOW)


class Ledger:
    """A restored database's collections, its ledger and the bucket's copy."""

    def __init__(self) -> None:
        self.contacts = InMemoryDocumentCollectionAdapter(ContactDocument)
        self.audit = InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        registry = InMemoryCollectionRegistry()
        registry.register(DocumentCollectionName("contacts"), self.contacts)
        registry.register(DocumentCollectionName("audit_log_entries"), self.audit)
        self.eraser = InMemoryBusinessRowEraserAdapter(registry)
        self.deletions = BusinessDeletionRepository(
            InMemoryDocumentCollectionAdapter(BusinessDeletionDocument)
        )
        self.mirror = InMemoryDeletionLedgerMirrorAdapter()

    def business_with_rows(self) -> BusinessId:
        business_id = BusinessId()
        for sample in COUNTRY_SAMPLES[:2]:
            contact = build_contact(sample, business_id)
            self.contacts.upsert(str(contact.id), contact)
        entry = sample_document(
            AuditLogEntryDocument, DocumentCollectionName("audit_log_entries")
        ).model_copy(update={"business_id": business_id})
        self.audit.upsert(f"audit-{business_id}", entry)
        return business_id

    def entry(self, business_id: BusinessId, *, completed: bool) -> None:
        sample = sample_document(
            BusinessDeletionDocument, DocumentCollectionName("business_deletions")
        )
        self.deletions.begin(
            sample.model_copy(
                update={
                    "id": deletion_id_for(business_id),
                    "deleted_business_id": business_id,
                    "completed_at": NOW if completed else None,
                }
            )
        )

    def mirrored(self, business_id: BusinessId) -> None:
        self.mirror.record(
            DeletionLedgerRecord(
                business_id=business_id,
                deletion_id=deletion_id_for(business_id),
                started_at=NOW,
            )
        )

    def contacts_of(self, business_id: BusinessId) -> int:
        return int(self.contacts.count_business_documents(business_id))

    def run(self) -> int:
        use_case = ReapplyDeletionLedgerUseCase(
            deletion_repo=self.deletions,
            ledger_mirror=self.mirror,
            row_eraser=self.eraser,
        )
        return int(use_case.run(TICK).processed_count)


def test_rows_of_a_deleted_business_that_came_back_go_again() -> None:
    ledger = Ledger()
    # Restored from before its entry: only the bucket's copy knows it.
    only_mirrored, finished = ledger.business_with_rows(), ledger.business_with_rows()
    ledger.mirrored(only_mirrored)
    ledger.entry(finished, completed=True)

    assert ledger.run() == 4

    assert ledger.contacts_of(only_mirrored) == 0
    assert ledger.contacts_of(finished) == 0
    # The audit log is what the law keeps.
    assert int(ledger.audit.count_business_documents(only_mirrored)) == 1
    assert ledger.run() == 0


def test_a_deletion_under_way_and_an_open_business_are_left_alone() -> None:
    ledger = Ledger()
    under_way, open_business = ledger.business_with_rows(), ledger.business_with_rows()
    ledger.mirrored(under_way)
    ledger.entry(under_way, completed=False)

    assert ledger.run() == 0

    assert ledger.contacts_of(under_way) == 2
    assert ledger.contacts_of(open_business) == 2


def test_the_daily_job_deletes_a_restored_business_again() -> None:
    with open_closure_world() as world:
        container = world.workshop.container
        business_id = BusinessId(world.business_b)
        with container.utilities.storage_scope().platform_wide():
            contacts = container.repositories.contact_repo()
            saved = contacts.list_by_business(business_id)[:3]
        world.delete_b_after_thirty_days()
        assert "contacts" not in world.rows_of(world.business_b)

        # A restore brings some of its rows back.
        with container.utilities.storage_scope().platform_wide():
            for contact in saved:
                contacts.save(contact)
        assert world.rows_of(world.business_b)["contacts"] == len(saved)
        world.workshop.clock.advance(DAY_SECONDS)
        before_a = world.rows_of(world.business_a)

        world.tick("reapply_deletion_ledger")

        assert "contacts" not in world.rows_of(world.business_b)
        assert world.rows_of(world.business_a) == before_a
