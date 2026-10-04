from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.support_access import SupportAccessQuery, SupportAccessView
from app.use_cases.businesses.support_access.support_access_views import (
    support_access_view,
)


class GetSupportAccessUseCase(UseCaseContract[SupportAccessQuery, SupportAccessView]):
    """
    Platform support in this business now (the cabinet's SupportBanner and
    Settings → Privacy): every open look into the cabinet with who, why
    and until when, and whether the owner lets support change things. The
    team sees it; so does a support admin during their own look (with
    whether they may change things right now).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        grant_repo: SupportAccessGrantRepoContract,
        user_repo: UserRepoContract,
        platform_admins: PlatformAdminRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._user_repo: UserRepoContract = user_repo
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SupportAccessQuery) -> SupportAccessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                access_mode=BusinessAccessMode.READ,
            )
        )
        return support_access_view(
            business,
            self._grant_repo.list_open(business.id),
            input_data.user_id,
            self._user_repo,
            self._platform_admins,
            self._wall_clock.now_unix(),
        )
