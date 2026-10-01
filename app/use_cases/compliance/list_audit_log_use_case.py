from app.contracts.repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.compliance import AuditLogEntryView, AuditLogQuery


class ListAuditLogUseCase(UseCaseContract[AuditLogQuery, list[AuditLogEntryView]]):
    """Owner reads the newest operations on personal data of the business."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def run(self, input_data: AuditLogQuery) -> list[AuditLogEntryView]:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        # A stable ascending sort reversed keeps entries written in the same
        # microsecond newest-first as well.
        oldest_first: list[AuditLogEntryDocument] = sorted(
            self._audit_log_repo.list_by_business(business.id),
            key=lambda entry: entry.created_at,
        )
        newest_entries: list[AuditLogEntryDocument] = oldest_first[::-1][
            : input_data.limit
        ]
        return [
            AuditLogEntryView(
                id=entry.id,
                action=entry.action,
                entity=entry.entity,
                entity_id=entry.entity_id,
                actor_id=entry.actor_id,
                ip_address=entry.ip_address,
                occurred_at=entry.created_at,
            )
            for entry in newest_entries
        ]
