from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.waitlist_repositories import (
    WaitlistEntryRepoContract,
    WaitlistSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.waitlist_views import (
    UpdateWaitlistSettingsCommand,
    WaitlistSettingsView,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.shared.operations_support import build_audit_entry
from app.use_cases.waitlist.waitlist_entry_views import (
    build_settings_view,
    stored_or_default,
)

WAITLIST_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("waitlist_settings")


class UpdateWaitlistSettingsUseCase(
    UseCaseContract[UpdateWaitlistSettingsCommand, WaitlistSettingsView]
):
    """
    The owner keeps a waitlist or not, and sets how long a freed place is
    held for a waiting customer (15 to 120 minutes). Turning it off keeps
    the entries (staff still see them) but offers nothing more, and the
    assistant stops offering the list. Owners only; audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        waitlist_settings_repo: WaitlistSettingsRepoContract,
        waitlist_entry_repo: WaitlistEntryRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._settings_repo: WaitlistSettingsRepoContract = waitlist_settings_repo
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateWaitlistSettingsCommand) -> WaitlistSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        settings = stored_or_default(
            self._settings_repo.get_by_business(business.id), business.id, now
        ).model_copy(
            update={
                "is_enabled": input_data.request.is_enabled,
                "hold_minutes": input_data.request.hold_minutes,
                "updated_by": input_data.user_id,
                "updated_at": now,
            }
        )
        self._settings_repo.save(settings)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.UPDATE,
                WAITLIST_SETTINGS_ENTITY,
                str(settings.id),
                now,
            )
        )
        return build_settings_view(
            settings, self._entry_repo.count_by_status(business.id)
        )
