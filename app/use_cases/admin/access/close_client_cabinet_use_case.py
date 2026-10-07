from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import (
    PlatformAdminPermission,
    SupportAccessEndReason,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.support_access import (
    CloseClientCabinetCommand,
    SupportAccessEnding,
)
from app.use_cases.shared.support_access import end_grant, live_sessions


class CloseClientCabinetUseCase(UseCaseContract[CloseClientCabinetCommand, None]):
    """
    A platform admin ends their own look into a client's cabinet before
    its hour is over ("Leave the cabinet"): audited SUPPORT_ACCESS_END with
    the address; the owner's banner goes away. Nothing open is no error.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        grant_repo: SupportAccessGrantRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CloseClientCabinetCommand) -> None:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.OPEN_CLIENT_CABINET,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        grants = self._grant_repo.list_open_of_admin(input_data.business_id, admin.id)
        for grant in live_sessions(grants, now):
            end_grant(
                self._grant_repo,
                self._audit_log_repo,
                grant,
                SupportAccessEnding(
                    ended_at=now,
                    ended_by=admin.id,
                    reason=SupportAccessEndReason.CLOSED_BY_ADMIN,
                ),
                input_data.client_ip_address,
            )
