from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_sessions import EndMemberSessionsCommand
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.sessions import RevokedSessionsView, SessionSweep
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.session_sweeps import end_sessions, own_session


class EndMemberSessionsUseCase(
    UseCaseContract[EndMemberSessionsCommand, RevokedSessionsView]
):
    """
    A platform admin who may change clients' accounts (SUPER) ends every
    session of one member of a client's team, at once, on every device: a
    stolen phone, a suspected takeover. The person signs in again; their
    next request with an old token is refused. Needs a fresh confirmation
    (step-up). Audited in the platform's chain as SESSION_REVOKED about the
    person, by the admin, with the count and the admin's address (people
    and sessions are platform rows: the operation runs outside any
    business's scope). Admins ending their own sessions keep the one they
    act from. A member of another business, or an unknown one, is not
    found.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        business_repo: BusinessRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: EndMemberSessionsCommand) -> RevokedSessionsView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.CHANGE_CLIENT_CABINET,
            )
        )
        self._step_up.require_recent_authentication()
        business: BusinessDocument = require_business(
            self._business_repo, input_data.client_id
        )
        if not any(
            member.user_id == input_data.member_user_id for member in business.members
        ):
            raise NotFoundError(
                f"Member {input_data.member_user_id} of business {business.id} "
                "was not found."
            )

        now: Microseconds = self._wall_clock.now_unix()
        ended: DocumentCount = end_sessions(
            self._user_session_repo,
            self._audit_log_repo,
            SessionSweep(
                user_id=input_data.member_user_id,
                actor_id=admin.id,
                reason=SessionSweepReason.ENDED_BY_PLATFORM_ADMIN,
                kept_session_id=own_session(
                    self._session_assurance, input_data.member_user_id
                ),
                client_ip_address=input_data.client_ip_address,
                now=now,
            ),
        )
        return RevokedSessionsView(revoked_count=ended)
