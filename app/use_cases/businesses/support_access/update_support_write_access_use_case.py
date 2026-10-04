from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import SupportAccessEndReason, SupportAccessKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.support_access import (
    SupportAccessEnding,
    SupportAccessView,
    UpdateSupportWriteAccessCommand,
)
from app.use_cases.businesses.support_access.support_access_views import (
    require_owner_member,
    support_access_view,
)
from app.use_cases.shared.support_access import (
    DEFAULT_WRITE_ACCESS_HOURS,
    MICROSECONDS_PER_MINUTE,
    audit_support_access,
    end_grant,
    is_live,
)


class UpdateSupportWriteAccessUseCase(
    UseCaseContract[UpdateSupportWriteAccessCommand, SupportAccessView]
):
    """
    The owner lets platform support change things in the cabinet for some
    hours (a day by default, a week at most), or stops it at once.

    Only an owner of the business decides (never support itself). Turning
    it on needs a fresh confirmation (step-up) and replaces an earlier
    consent; turning it off ends any. Each is audited (UPDATE of
    `support_write_access`, with the address). Support with a SUPER role
    may then change what staff may change, until the consent ends.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        grant_repo: SupportAccessGrantRepoContract,
        audit_log_repo: AuditLogRepoContract,
        user_repo: UserRepoContract,
        platform_admins: PlatformAdminRegistryContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._user_repo: UserRepoContract = user_repo
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up

    def run(self, input_data: UpdateSupportWriteAccessCommand) -> SupportAccessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        require_owner_member(business, input_data.user_id)
        if input_data.is_allowed:
            self._step_up.require_recent_authentication()

        now: Microseconds = self._wall_clock.now_unix()
        for grant in self._grant_repo.list_open(business.id):
            if grant.kind is SupportAccessKind.WRITE_CONSENT and is_live(grant, now):
                end_grant(
                    self._grant_repo,
                    self._audit_log_repo,
                    grant,
                    SupportAccessEnding(
                        ended_at=now,
                        ended_by=input_data.user_id,
                        reason=SupportAccessEndReason.REVOKED_BY_OWNER,
                    ),
                    input_data.client_ip_address,
                )

        if input_data.is_allowed:
            self._allow(input_data, business, now)

        return support_access_view(
            business,
            self._grant_repo.list_open(business.id),
            input_data.user_id,
            self._user_repo,
            self._platform_admins,
            now,
        )

    def _allow(
        self,
        command: UpdateSupportWriteAccessCommand,
        business: BusinessDocument,
        now: Microseconds,
    ) -> None:
        hours: int = (
            DEFAULT_WRITE_ACCESS_HOURS if command.hours is None else int(command.hours)
        )
        consent = SupportAccessGrantDocument(
            business_id=business.id,
            kind=SupportAccessKind.WRITE_CONSENT,
            granted_by=command.user_id,
            expires_at=Microseconds(int(now) + hours * 60 * MICROSECONDS_PER_MINUTE),
            created_at=now,
            updated_at=now,
        )
        self._grant_repo.save(consent)
        audit_support_access(
            self._audit_log_repo,
            consent,
            AuditAction.UPDATE,
            actor_id=command.user_id,
            client_ip_address=command.client_ip_address,
            now=now,
        )
