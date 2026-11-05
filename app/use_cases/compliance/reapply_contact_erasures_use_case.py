import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.contact_erasure_ledger import ContactErasureLedgerAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.dto.compliance import ContactRecords, ContactRecordsQuery
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.compliance.contact_data_eraser import ContactDataEraser

logger: logging.Logger = logging.getLogger(__name__)

CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")


class ReapplyContactErasuresUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job "reapply_contact_erasures" (daily, the batch worker): a
    database restored from a backup (a point-in-time recovery, the
    off-site backup) older than a customer's erasure holds that customer's
    data again. Every erasure the ledger outside the database names
    (`ContactErasureLedgerAdapterContract`) whose contact is back with its
    data is erased again (`ContactDataEraser`, the same erasure as the
    owner's), inside the storage scope of the record's business, audited
    as DELETE of the contact without an actor; a contact still erased, or
    gone with its business, is left alone. One erasure failing never stops
    the others; the run then fails, so it is retried and reported.
    """

    def __init__(
        self,
        ledger: ContactErasureLedgerAdapterContract,
        contact_repo: ContactRepoContract,
        collect_contact_records: UseCaseContract[ContactRecordsQuery, ContactRecords],
        eraser: ContactDataEraser,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._storage_scope: StorageScopeContract = storage_scope
        self._ledger: ContactErasureLedgerAdapterContract = ledger
        self._contact_repo: ContactRepoContract = contact_repo
        self._collect_contact_records: UseCaseContract[
            ContactRecordsQuery, ContactRecords
        ] = collect_contact_records
        self._eraser: ContactDataEraser = eraser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        erased: int = 0
        failed: int = 0
        for record in self._ledger.read_all():
            try:
                with self._storage_scope.scoped_to_business(record.business_id):
                    erased += int(self._erase_again(record))
            except Exception:  # noqa: BLE001 - one erasure never stops the others
                failed += 1
                logger.exception(
                    "Contact erasure ledger: %s of %s could not be erased again",
                    record.contact_id,
                    record.business_id,
                )

        if failed:
            raise ExternalServiceError(
                f"{failed} erasures of the ledger could not be applied again."
            )

        return JobReport(processed_count=ProcessedItemCount(erased))

    def _erase_again(self, record: ContactErasureRecord) -> bool:
        contact: ContactDocument | None = self._contact_repo.get(
            record.business_id, record.contact_id
        )
        if contact is None or contact.erased_at is not None:
            return False

        records: ContactRecords = self._collect_contact_records.run(
            ContactRecordsQuery(
                business_id=record.business_id, contact_id=record.contact_id
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._eraser.erase(records, now)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=record.business_id,
                action=AuditAction.DELETE,
                entity=CONTACT_ENTITY,
                entity_id=AuditEntityReference(str(record.contact_id)),
                created_at=now,
                updated_at=now,
            )
        )
        logger.warning(
            "Contact erasure ledger: erased customer %s of %s had their data "
            "again (a restore?); erased it again",
            record.contact_id,
            record.business_id,
        )
        return True
