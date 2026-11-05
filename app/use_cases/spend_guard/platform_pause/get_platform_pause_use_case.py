from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_safety import (
    PlatformPauseRepoContract,
    PlatformSpendGaugeContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_pause import PlatformPauseQuery, PlatformPauseView
from app.use_cases.spend_guard.platform_pause.platform_pause_views import (
    build_platform_pause_view,
)
from app.utilities.spend.platform_brakes import (
    read_budget_stop,
)


class GetPlatformPauseUseCase(UseCaseContract[PlatformPauseQuery, PlatformPauseView]):
    """
    The admin system page's "Platform brakes" card: whether every assistant
    is paused (who paused them, when and why), and how the daily budget
    stop stands (today's share of the budget, the share it stops at,
    whether it holds). Any platform admin who sees operations may look;
    only a SUPER admin may pause (`SetPlatformPauseUseCase`).
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        platform_pause_repo: PlatformPauseRepoContract,
        platform_spend_gauge: PlatformSpendGaugeContract,
        settings: SpendGuardSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._pause_repo: PlatformPauseRepoContract = platform_pause_repo
        self._spend_gauge: PlatformSpendGaugeContract = platform_spend_gauge
        self._settings: SpendGuardSettings = settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PlatformPauseQuery) -> PlatformPauseView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        pause: PlatformPauseDocument | None = self._pause_repo.get()
        return build_platform_pause_view(
            pause,
            read_budget_stop(
                self._spend_gauge, self._settings, self._wall_clock.now_unix()
            ),
            self._settings,
        )
