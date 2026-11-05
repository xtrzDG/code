from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.deposits.deposit_views import (
    DepositRequestQuery,
    DepositRequestView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.deposits.deposit_request_views import build_request_view


class GetDepositRequestUseCase(
    UseCaseContract[DepositRequestQuery, DepositRequestView]
):
    """
    One deposit for the booking card: amount, reference to look for in the
    merchant account, page, state and its moments. Owners and staff.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        deposit_request_repo: DepositRequestRepoContract,
        deposit_settings_repo: DepositSettingsRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._request_repo: DepositRequestRepoContract = deposit_request_repo
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo

    def run(self, input_data: DepositRequestQuery) -> DepositRequestView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        request = self._request_repo.get(business.id, input_data.request_id)
        if request is None:
            raise NotFoundError(f"Deposit {input_data.request_id} was not found.")

        return build_request_view(
            request, self._settings_repo.get_by_business(business.id)
        )
