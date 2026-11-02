from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.dto.compliance import (
    ContactDataCommand,
    ContactErasureResult,
    ContactRecords,
    ContactRecordsQuery,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.compliance.contact_data_eraser import ContactDataEraser
from app.use_cases.compliance.record_contact_erasure_use_case import (
    RECORD_CONTACT_ERASURE_JOB,
)


class DeleteContactDataUseCase(
    UseCaseContract[ContactDataCommand, ContactErasureResult]
):
    """
    Owner erases one visitor's personal data (right to erasure), after a
    fresh sign-in (step-up): `ContactDataEraser` erases what the platform
    keeps of them. The erasure then goes into the ledger outside the
    database (the queued job "record_contact_erasure", retried until the
    backup bucket takes it), so a restore from a backup taken before it
    erases them again (`ReapplyContactErasuresUseCase`). The erasure is
    audited with the contact id only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        collect_contact_records: UseCaseContract[ContactRecordsQuery, ContactRecords],
        eraser: ContactDataEraser,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._collect_contact_records: UseCaseContract[
            ContactRecordsQuery,
            ContactRecords,
        ] = collect_contact_records
        self._eraser: ContactDataEraser = eraser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def run(self, input_data: ContactDataCommand) -> ContactErasureResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        records: ContactRecords = self._collect_contact_records.run(
            ContactRecordsQuery(
                business_id=business.id,
                contact_id=input_data.contact_id,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        result: ContactErasureResult = self._eraser.erase(records, now)
        self._job_queue.enqueue(
            RECORD_CONTACT_ERASURE_JOB,
            JobPayloadJson(
                ContactErasureRecord(
                    business_id=business.id,
                    contact_id=records.contact.id,
                    erased_at=now,
                ).model_dump_json()
            ),
            business_id=business.id,
            # The batch worker's lane: it holds the bucket's ledger key.
            lane=JobLane.DEFAULT,
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=AuditEntityName("contact"),
                entity_id=AuditEntityReference(str(records.contact.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return result
