from app.contracts.platform_admins import (
    PlatformAdminCheck,
    PlatformAdminRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import (
    PlatformAdminAccessRequest,
    PlatformAdminTeamQuery,
    PlatformAdminTeamView,
)
from app.use_cases.admin.team.admin_team import team_view


class ListPlatformAdminsUseCase(
    UseCaseContract[PlatformAdminTeamQuery, PlatformAdminTeamView]
):
    """The admin team (Team page; SUPER admins only)."""

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        platform_admin_repo: PlatformAdminRepoContract,
        user_repo: UserRepoContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._platform_admin_repo: PlatformAdminRepoContract = platform_admin_repo
        self._user_repo: UserRepoContract = user_repo

    def run(self, input_data: PlatformAdminTeamQuery) -> PlatformAdminTeamView:
        viewer: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_ADMINS,
            )
        )
        return team_view(self._platform_admin_repo, self._user_repo, viewer.id)
