from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.platform_admins import (
    PlatformAdminCheck,
    PlatformAdminRegistryContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import (
    PlatformAdminPermission,
    SupportAccessEndReason,
    SupportAccessKind,
)
from app.schemas.constants.client_health import CabinetSection
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import ClientCabinetAccess, OpenClientCabinetCommand
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.support_access import SupportAccessEnding
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.support_access import (
    MICROSECONDS_PER_MINUTE,
    SUPPORT_SESSION_MINUTES,
    audit_support_access,
    can_support_write,
    end_grant,
    live_sessions,
)
from app.utilities.security.support_access_texts import SupportAccessTexts

# Telegram chats and e-mail of the team hear it (no paid SMS); every
# member's device too.
NOTICE_CHANNELS: list[ManagerContactChannel] = [
    ManagerContactChannel.TELEGRAM,
    ManagerContactChannel.EMAIL,
]


class OpenClientCabinetUseCase(
    UseCaseContract[OpenClientCabinetCommand, ClientCabinetAccess]
):
    """
    A platform admin looks into a client's cabinet: least privilege, with a
    reason, for a limited time and visibly to the owner.

    Needs a role that opens client cabinets (SUPER, SUPPORT_READONLY), a
    fresh confirmation (step-up) and a reason. Opens a support access
    grant for an hour (an earlier open one of the same admin is replaced),
    read-only unless the owner allowed changes; audits SUPPORT_ACCESS_START
    with the address; and tells the team (devices, Telegram chats and
    e-mail) who opened it and why. The cabinet shows a banner while it
    lasts, where the owner can end it.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        platform_admins: PlatformAdminRegistryContract,
        business_repo: BusinessRepoContract,
        grant_repo: SupportAccessGrantRepoContract,
        audit_log_repo: AuditLogRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._business_repo: BusinessRepoContract = business_repo
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up

    def run(self, input_data: OpenClientCabinetCommand) -> ClientCabinetAccess:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.OPEN_CLIENT_CABINET,
            )
        )
        self._step_up.require_recent_authentication()
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        grants: list[SupportAccessGrantDocument] = self._grant_repo.list_open(
            business.id
        )
        for earlier in live_sessions(grants, now):
            if earlier.admin_user_id == admin.id:
                end_grant(
                    self._grant_repo,
                    self._audit_log_repo,
                    earlier,
                    SupportAccessEnding(
                        ended_at=now,
                        ended_by=admin.id,
                        reason=SupportAccessEndReason.REPLACED,
                    ),
                    input_data.client_ip_address,
                )

        grant = SupportAccessGrantDocument(
            business_id=business.id,
            kind=SupportAccessKind.SESSION,
            granted_by=admin.id,
            admin_user_id=admin.id,
            reason=input_data.reason,
            opened_from_ip=input_data.client_ip_address,
            expires_at=Microseconds(
                int(now) + SUPPORT_SESSION_MINUTES * MICROSECONDS_PER_MINUTE
            ),
            created_at=now,
            updated_at=now,
        )
        self._grant_repo.save(grant)
        entry_id: AuditLogEntryId = audit_support_access(
            self._audit_log_repo,
            grant,
            AuditAction.SUPPORT_ACCESS_START,
            actor_id=admin.id,
            client_ip_address=input_data.client_ip_address,
            now=now,
        )
        self._tell_the_team(business, admin, grant)
        return ClientCabinetAccess(
            business_id=business.id,
            business_name=business.name,
            country_code=business.country_code,
            owner_language=business.owner_language,
            sections=list(CabinetSection),
            audit_log_entry_id=entry_id,
            opened_at=now,
            support_access_grant_id=grant.id,
            expires_at=grant.expires_at,
            can_write=can_support_write(
                self._platform_admins.role_of(admin), grants, now
            ),
        )

    def _tell_the_team(
        self,
        business: BusinessDocument,
        admin: UserDocument,
        grant: SupportAccessGrantDocument,
    ) -> None:
        if grant.reason is None:
            return

        self._staff_alerts.alert(
            business,
            StaffAlert(
                business_id=business.id,
                target=StaffLinkTarget.OVERVIEW,
                tag=PushNotificationTag(f"support_access:{grant.id}"),
                subject=StaffAlertSubject(f"support_access:{grant.id}"),
                contact_channels=NOTICE_CHANNELS,
            ),
            SupportAccessTexts(self._resolver, admin.display_name, grant.reason),
        )
