from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import (
    PlatformAdminCheck,
    PlatformAdminRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import (
    PlatformAdminAccessRequest,
    RemovePlatformAdminCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.admin.team.admin_session_ending import AdminSessionEnding
from app.use_cases.admin.team.admin_team import (
    audit_team_change,
    refuse_losing_last_super,
)


class RemovePlatformAdminUseCase(UseCaseContract[RemovePlatformAdminCommand, None]):
    """
    A SUPER admin takes someone off the admin team: every session of
    theirs ends (AdminSessionEnding), so their next request finds no admin
    rights and they sign in again as an ordinary person. The team always
    keeps a SUPER admin (ConflictError). Needs a fresh confirmation
    (step-up); audited as PLATFORM_ADMIN_CHANGED.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        platform_admin_repo: PlatformAdminRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._platform_admin_repo: PlatformAdminRepoContract = platform_admin_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up
        self._sessions: AdminSessionEnding = AdminSessionEnding(
            user_repo, user_session_repo, session_assurance, audit_log_repo
        )

    def run(self, input_data: RemovePlatformAdminCommand) -> None:
        actor: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_ADMINS,
            )
        )
        self._step_up.require_recent_authentication()
        admin: PlatformAdminDocument | None = self._platform_admin_repo.get(
            input_data.admin_id
        )
        if admin is None:
            raise NotFoundError(f"Platform admin {input_data.admin_id} was not found.")

        refuse_losing_last_super(self._platform_admin_repo, admin, new_role=None)
        now: Microseconds = self._wall_clock.now_unix()
        self._platform_admin_repo.delete(admin.id)
        audit_team_change(
            self._audit_log_repo,
            actor.id,
            admin,
            input_data.client_ip_address,
            now,
            is_removed=True,
        )
        self._sessions.end(admin, actor.id, input_data.client_ip_address, now)
