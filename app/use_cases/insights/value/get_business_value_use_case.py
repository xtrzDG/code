"""The value of a period for a member of the business (dashboard hero, chips)."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_model import ValueModel, ValueModelQuery
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.use_cases.insights.value.value_access import (
    choose_value_dates,
    local_today,
    sees_money,
    value_model_query,
    without_money,
)


class GetBusinessValueUseCase(UseCaseContract[BusinessValueQuery, ValueModel]):
    """
    What the assistant did in a period and the period before, for owners
    and staff of the business. Staff get the counts without any amount
    (no average check, no money estimate). Counts only, no personal data,
    so no audit entry.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        compute_value_model: UseCaseContract[ValueModelQuery, ValueModel],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._compute_value_model: UseCaseContract[ValueModelQuery, ValueModel] = (
            compute_value_model
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessValueQuery) -> ValueModel:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        model: ValueModel = self._compute_value_model.run(
            value_model_query(
                business,
                choose_value_dates(input_data, local_today(business, self._wall_clock)),
            )
        )
        return (
            model if sees_money(business, input_data.user_id) else without_money(model)
        )
