"""The value model of a business for a period and the period before it."""

from datetime import date
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.value.value_model import (
    ValueModel,
    ValueModelQuery,
    ValueTotals,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.use_cases.insights.value.value_counting import (
    ValueSources,
    ValueWindow,
    count_value_totals,
)
from app.use_cases.insights.value.value_estimates import (
    EstimateCatalogs,
    ValueEstimates,
    estimate_business_value,
    read_weekly_hours,
)
from app.use_cases.insights.value.value_return import (
    NO_RETURN,
    PlanPrices,
    PlanReturn,
    plan_return,
    read_plan_terms,
)
from app.use_cases.shared.business_access import require_business
from app.utilities.scheduling.opening_hours import DayRanges
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    parse_local_date,
)


class ComputeValueModelUseCase(UseCaseContract[ValueModelQuery, ValueModel]):
    """
    What the assistant did for a business and what it is worth, for local
    dates of the business time zone, next to the period before (one
    computation for the dashboard, the digests and the monthly report):

    - bookings the assistant made in its conversations and kept (not
      cancelled, not a no-show) at their own values (the booked service's
      price, a stay's nightly rates), and those without a value times the
      average check: the owner's, or the niche's typical check in the
      business currency; the totals say which (`revenue_source`); for
      niches that take orders, the requests it took instead of bookings;
    - conversations after hours (flagged, or started while closed);
    - staff minutes saved: the assistant's replies times the niche's
      minutes per reply, plus the calls it answered times its minutes per
      call;
    - what the money returned against the plan's price for the same days
      (`value_return.py`; only with `plan_prices`); in the free trial no
      cost and no multiple, only the monthly price after it.

    Everything is counted by the database; sandbox activity is excluded.
    Callers check access (the cabinet route, the report job).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        sources: ValueSources,
        catalogs: EstimateCatalogs,
        plan_prices: PlanPrices | None = None,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._sources: ValueSources = sources
        self._catalogs: EstimateCatalogs = catalogs
        self._plan_prices: PlanPrices | None = plan_prices

    def run(self, input_data: ValueModelQuery) -> ValueModel:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        estimates: ValueEstimates = estimate_business_value(self._catalogs, business)
        weekly_hours: DayRanges | None = read_weekly_hours(
            self._business_profile_repo, self._schedule_exception_repo, business
        )
        earliest: date = min(
            parse_local_date(input_data.previous_date_from),
            parse_local_date(input_data.date_from),
        )
        sandbox_ids: list[ConversationId] = (
            self._sources.conversation_repo.list_sandbox_active_since(
                business.id,
                Microseconds(local_day_start_microseconds(earliest, zone)),
            )
        )

        def window(date_from: LocalDate, date_to: LocalDate) -> ValueWindow:
            return ValueWindow(
                business_id=business.id,
                zone=zone,
                weekly_hours=weekly_hours,
                date_from=parse_local_date(date_from),
                date_to=parse_local_date(date_to),
                sandbox_ids=sandbox_ids,
            )

        current: ValueTotals = count_value_totals(
            self._sources,
            window(input_data.date_from, input_data.date_to),
            estimates.rates,
        )
        returned: PlanReturn = (
            NO_RETURN
            if self._plan_prices is None
            else plan_return(
                read_plan_terms(self._plan_prices, business),
                business.currency_code,
                parse_local_date(input_data.date_from),
                parse_local_date(input_data.date_to),
                current.estimated_revenue_minor,
            )
        )
        return ValueModel(
            business_id=business.id,
            currency_code=business.currency_code,
            timezone=business.timezone,
            date_from=input_data.date_from,
            date_to=input_data.date_to,
            previous_date_from=input_data.previous_date_from,
            previous_date_to=input_data.previous_date_to,
            value_basis=estimates.rates.basis,
            average_check_minor=estimates.rates.average_check,
            average_check_source=estimates.source,
            typical_check_minor=estimates.typical_check,
            seconds_per_reply=estimates.rates.seconds_per_reply,
            seconds_per_call=estimates.rates.seconds_per_call,
            current=current,
            previous=count_value_totals(
                self._sources,
                window(input_data.previous_date_from, input_data.previous_date_to),
                estimates.rates,
            ),
            plan_cost_minor=returned.plan_cost_minor,
            return_multiple=returned.return_multiple,
            is_trial=returned.is_trial,
            trial_ends_at=returned.trial_ends_at,
            plan_cost_after_trial_minor=returned.price_after_trial,
        )
