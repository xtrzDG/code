from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.deposit_repositories import (
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deposits.deposit_settings import (
    DepositSettingsQuery,
    DepositSettingsView,
)
from app.use_cases.deposits.deposit_settings_views import (
    build_settings_view,
    stored_or_default,
)


class GetDepositSettingsUseCase(
    UseCaseContract[DepositSettingsQuery, DepositSettingsView]
):
    """
    A business's deposits: on or off, the hold, the refund cutoff, the
    payment pages (one that carries a key shows only its host and path)
    and the policies of its resources, services and banquets, with the
    business currency's digits. Owners and staff (the cards show the
    policies); never stored by reading.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        deposit_settings_repo: DepositSettingsRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DepositSettingsQuery) -> DepositSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return build_settings_view(
            stored_or_default(
                self._settings_repo.get_by_business(business.id),
                business.id,
                self._wall_clock.now_unix(),
            ),
            business,
        )
