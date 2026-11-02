from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin_sessions import ClientMemberSessionList, ClientMembersQuery
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.use_cases.admin.sessions.client_member_sessions import member_sessions_view
from app.use_cases.shared.business_access import require_business


class ListClientMemberSessionsUseCase(
    UseCaseContract[ClientMembersQuery, ClientMemberSessionList]
):
    """
    A platform admin who sees clients looks at a client's team: each
    member's role, name and masked phone or e-mail, how many sessions they
    have signed in and when one was last used (owners first, as stored).
    The sessions themselves (devices, addresses) stay the person's own; a
    team has a handful of members, each read by an indexed lookup.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ClientMembersQuery) -> ClientMemberSessionList:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_CLIENTS,
            )
        )
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        return ClientMemberSessionList(
            items=[
                member_sessions_view(
                    member,
                    self._user_repo.get(member.user_id),
                    self._user_session_repo.list_by_user(member.user_id),
                    now,
                )
                for member in business.members
            ]
        )
