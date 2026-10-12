from app.contracts.repositories.audit_chain_repositories import (
    AuditActivityRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.audit_chain_views import (
    PlatformAuditEntryView,
    PlatformAuditLogPage,
    PlatformAuditLogQuery,
)
from app.schemas.dto.audit_trail import PlatformAuditFilter
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListPlatformAuditLogUseCase(
    UseCaseContract[PlatformAuditLogQuery, PlatformAuditLogPage]
):
    """
    The platform admin's audit view: the entries that name no business
    (sign-ins, failed checks and lockouts, sign-outs, two-factor changes,
    the admin team, key rotations, platform purges), newest first by their
    place in the platform's chain, one keyset page at a time, optionally of
    one operation or security event (filtered before paging).

    Raises:
        AccessDeniedError: the user may not see the platform's operations.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        audit_activity_repo: AuditActivityRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._audit_activity_repo: AuditActivityRepoContract = audit_activity_repo

    def run(self, input_data: PlatformAuditLogQuery) -> PlatformAuditLogPage:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        entries: list[AuditLogEntryDocument]
        entries, next_cursor = finish_page(
            self._audit_activity_repo.page_platform_entries(
                read_slice(input_data.page),
                PlatformAuditFilter(
                    action=input_data.action,
                    security_event=input_data.security_event,
                ),
            ),
            input_data.page,
            sort_key=lambda entry: int(entry.chain_position or 0),
            item_id=lambda entry: str(entry.id),
        )
        return PlatformAuditLogPage(
            items=[platform_entry_view(entry) for entry in entries],
            next_cursor=next_cursor,
        )


def platform_entry_view(entry: AuditLogEntryDocument) -> PlatformAuditEntryView:
    return PlatformAuditEntryView(
        id=entry.id,
        chain_position=entry.chain_position,
        action=entry.action,
        security_event=entry.security_event,
        entity=entry.entity,
        entity_id=entry.entity_id,
        actor_id=entry.actor_id,
        ip_address=entry.ip_address,
        occurred_at=entry.created_at,
        record_count=entry.record_count,
    )
