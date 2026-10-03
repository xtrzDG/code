from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.inbox_repositories import InboxSettingsRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.inbox_settings import (
    InboxSettingsView,
    UpdateInboxSettingsCommand,
)
from app.use_cases.inbox.inbox_support import (
    INBOX_SETTINGS_ENTITY,
    append_audit,
    require_members,
)
from app.use_cases.inbox.settings.settings_views import build_settings_view


class UpdateInboxSettingsUseCase(
    UseCaseContract[UpdateInboxSettingsCommand, InboxSettingsView]
):
    """
    An owner turns automatic assignment of new handoffs and new requests on
    or off and chooses who takes turns (members only, 422 `not_a_member`;
    none chosen: every staff member, or the owners when there is no staff).
    Audited (UPDATE of "inbox_settings").
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        inbox_settings_repo: InboxSettingsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._inbox_settings_repo: InboxSettingsRepoContract = inbox_settings_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateInboxSettingsCommand) -> InboxSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        chosen = list(dict.fromkeys(input_data.request.auto_assign_user_ids))
        require_members(business, chosen)
        now: Microseconds = self._wall_clock.now_unix()

        def update(stored: InboxSettingsDocument) -> None:
            stored.auto_assign_new_handoffs = (
                input_data.request.auto_assign_new_handoffs
            )
            stored.auto_assign_new_requests = (
                input_data.request.auto_assign_new_requests
            )
            stored.auto_assign_user_ids = chosen

        settings = self._inbox_settings_repo.change(business.id, update, now)
        append_audit(
            self._audit_log_repo,
            business.id,
            input_data.user_id,
            AuditAction.UPDATE,
            INBOX_SETTINGS_ENTITY,
            str(settings.id),
            input_data.client_ip_address,
            now,
        )
        return build_settings_view(business.id, settings)
