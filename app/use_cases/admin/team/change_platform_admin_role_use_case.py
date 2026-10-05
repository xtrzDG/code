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
    ChangePlatformAdminRoleCommand,
    PlatformAdminAccessRequest,
    PlatformAdminTeamView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.admin.team.admin_session_ending import AdminSessionEnding
from app.use_cases.admin.team.admin_team import (
    audit_team_change,
    refuse_losing_last_super,
    team_view,
)


class ChangePlatformAdminRoleUseCase(
    UseCaseContract[ChangePlatformAdminRoleCommand, PlatformAdminTeamView]
):
    """
    A SUPER admin gives a team member another role: their sessions end,
    so they sign in again under the new role (AdminSessionEnding). The
    team always keeps a SUPER admin (ConflictError). Needs a fresh
    confirmation (step-up); audited as PLATFORM_ADMIN_CHANGED.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        platform_admin_repo: PlatformAdminRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._platform_admin_repo: PlatformAdminRepoContract = platform_admin_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up
        self._sessions: AdminSessionEnding = AdminSessionEnding(
            user_repo, user_session_repo, session_assurance, audit_log_repo
        )

    def run(self, input_data: ChangePlatformAdminRoleCommand) -> PlatformAdminTeamView:
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

        if admin.role is not input_data.role:
            refuse_losing_last_super(self._platform_admin_repo, admin, input_data.role)
            now: Microseconds = self._wall_clock.now_unix()
            admin.role = input_data.role
            admin.updated_at = now
            self._platform_admin_repo.save(admin)
            audit_team_change(
                self._audit_log_repo,
                actor.id,
                admin,
                input_data.client_ip_address,
                now,
            )
            self._sessions.end(admin, actor.id, input_data.client_ip_address, now)

        return team_view(self._platform_admin_repo, self._user_repo, actor.id)
