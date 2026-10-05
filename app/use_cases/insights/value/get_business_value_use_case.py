"""The value of a period for a member of the business (dashboard hero, chips)."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import ActivationEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_model import ValueModel, ValueModelQuery
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.use_cases.insights.value.launch_floor import (
    LaunchFloor,
    floored_dates,
    read_launch_floor,
)
from app.use_cases.insights.value.value_access import (
    choose_value_dates,
    local_today,
    sees_money,
    value_model_query,
    without_money,
)
from app.utilities.value.value_periods import ValueDates


class GetBusinessValueUseCase(UseCaseContract[BusinessValueQuery, ValueModel]):
    """
    What the assistant did in a period and the period before, for owners
    and staff of the business. The period never starts before the business
    went live (or was created): asked from earlier, it starts on that day
    and says so (`is_since_launch`), compared with as many days before.
    Staff get the counts without any amount (no average check, no money
    estimate, no plan price). Counts only, no personal data, so no audit
    entry.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        compute_value_model: UseCaseContract[ValueModelQuery, ValueModel],
        activation_event_repo: ActivationEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._compute_value_model: UseCaseContract[ValueModelQuery, ValueModel] = (
            compute_value_model
        )
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessValueQuery) -> ValueModel:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        asked: ValueDates = choose_value_dates(
            input_data, local_today(business, self._wall_clock)
        )
        floor: LaunchFloor = read_launch_floor(self._activation_event_repo, business)
        dates: ValueDates = floored_dates(asked, floor)
        model: ValueModel = self._compute_value_model.run(
            value_model_query(business, dates)
        ).model_copy(
            update={
                "is_since_launch": dates.date_from > asked.date_from,
                "went_live_at": floor.went_live_at,
            }
        )
        return (
            model if sees_money(business, input_data.user_id) else without_money(model)
        )
