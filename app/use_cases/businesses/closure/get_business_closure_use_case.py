from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.business_closures import BusinessClosureReason
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.business_closures.closure_views import BusinessClosureView
from app.schemas.dto.businesses import BusinessQuery
from app.use_cases.businesses.closure.closure_reads import is_owner_of, is_paid_for
from app.use_cases.businesses.closure.closure_views import closure_view


class GetBusinessClosureUseCase(UseCaseContract[BusinessQuery, BusinessClosureView]):
    """
    Where a business stands on its way out, for anyone of its team: the
    cabinet's countdown banner on every page of a closing business and the
    danger zone of Settings → Business (owners may cancel).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        closure_repo: BusinessClosureRepoContract,
        subscription_repo: SubscriptionRepoContract,
        brand_repo: BrandRepoContract,
        user_repo: UserRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._user_repo: UserRepoContract = user_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessQuery) -> BusinessClosureView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        closure: BusinessClosureDocument | None = self._closure_repo.get(business.id)
        is_paid_again: bool = (
            closure is not None
            and closure.reason is BusinessClosureReason.UNPAID_SUBSCRIPTION
            and is_paid_for(
                self._subscription_repo, business, self._wall_clock.now_unix()
            )
        )
        return closure_view(
            business.id,
            closure,
            self._user_repo,
            is_owner_of(self._brand_repo, business, input_data.user_id),
            is_paid_again,
        )
