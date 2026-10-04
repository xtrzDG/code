from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.compliance import (
    ContactDataCommand,
    ContactDataExport,
    ContactRecords,
    ContactRecordsQuery,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)


class ExportContactDataUseCase(UseCaseContract[ContactDataCommand, ContactDataExport]):
    """
    Owner exports all personal data of one visitor (right of access).

    The export holds the contact, their conversations and messages, calls,
    bookings, leads, handoffs and the team's notes on their conversations,
    and is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        collect_contact_records: UseCaseContract[ContactRecordsQuery, ContactRecords],
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
    ) -> None:
        self._step_up: StepUpGuardContract = step_up
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._collect_contact_records: UseCaseContract[
            ContactRecordsQuery,
            ContactRecords,
        ] = collect_contact_records
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ContactDataCommand) -> ContactDataExport:
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
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.EXPORT,
                entity=AuditEntityName("contact"),
                entity_id=AuditEntityReference(str(records.contact.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return ContactDataExport(
            business_id=business.id,
            exported_at=now,
            records=records,
        )
