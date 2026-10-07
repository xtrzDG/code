"""
The value model: what the assistant did for a business in a period and
what that is worth, next to the period just before it. One computation
serves the dashboard, the digests and the monthly report.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.value import AverageCheckSource, RevenueSource, ValueBasis
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    TimezoneName,
)
from app.schemas.typings.value.booleans import IsPeriodSinceLaunch, IsTrialPeriod
from app.schemas.typings.value.constrained_floats import ValueReturnMultiple
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    BookedValueMinor,
    EstimatedRevenueMinor,
    MonthlyPlanPriceMinor,
    PlanCostMinor,
    StaffMinutesSaved,
    StaffSecondsPerCall,
    StaffSecondsPerReply,
)


class ValueModelQuery(ImmutableDTO):
    """
    The value of a business for local dates `date_from` to `date_to`
    (inclusive), compared with `previous_date_from` to `previous_date_to`.
    """

    business_id: BusinessId
    date_from: LocalDate
    date_to: LocalDate
    previous_date_from: LocalDate
    previous_date_to: LocalDate


class ValueTotals(ImmutableDTO):
    """
    What happened in one period (sandbox activity left out):

    - conversations that started, and those after hours (flagged by the
      conversation engine or started while the business was closed);
    - customer messages and the replies the assistant wrote;
    - phone calls the assistant answered (conversations of the phone line);
    - bookings made (as the dashboard counts them), and those the
      assistant made in a conversation that are still on (not cancelled,
      not a no-show);
    - requests taken and conversations handed to a person;
    - the staff minutes the replies and calls saved (rounded);
    - the money estimate: the assistant's bookings at their own values
      (`booked_value_minor`, for the `valued_booking_count` bookings of a
      priced service in the business currency) plus the others times the
      average check (or, for niches that take orders instead, its requests
      times the average check); `revenue_source` says which; None without
      either;
    - of the bookings kept, those the waitlist filled (a freed place a
      waiting customer took) and those a rebooking campaign brought back,
      each with their own values in the business currency (None: none had
      one): the growth the assistant made, not only what came in by itself.
    """

    conversation_count: PeriodItemCount
    after_hours_conversation_count: PeriodItemCount
    customer_message_count: PeriodItemCount
    assistant_reply_count: PeriodItemCount
    call_count: PeriodItemCount
    booking_count: PeriodItemCount
    assistant_booking_count: PeriodItemCount
    request_count: PeriodItemCount
    handoff_count: PeriodItemCount
    staff_minutes_saved: StaffMinutesSaved
    estimated_revenue_minor: EstimatedRevenueMinor | None = None
    valued_booking_count: PeriodItemCount = PeriodItemCount(0)
    booked_value_minor: BookedValueMinor | None = None
    revenue_source: RevenueSource | None = None
    waitlist_booking_count: PeriodItemCount = PeriodItemCount(0)
    waitlist_value_minor: BookedValueMinor | None = None
    campaign_booking_count: PeriodItemCount = PeriodItemCount(0)
    campaign_value_minor: BookedValueMinor | None = None


class ValueModel(ImmutableDTO):
    """
    The value of a business in a period and the period before it, in the
    business currency and time zone. `average_check_minor` is the owner's
    (`OWNER`) or the niche's typical check in the business currency
    (`NICHE_DEFAULT`, also given as `typical_check_minor`); without either
    there is no money estimate. The staff time rates explain the minutes.
    `plan_cost_minor` is what the business's plan costs for the period's
    days and `return_multiple` how many times the period's money estimate
    covers it (both None when the plan is priced in another currency; no
    multiple without an estimate, or for an estimate of nothing).

    In the free trial (`is_trial`, until `trial_ends_at`) the period costs
    nothing: no plan cost and no multiple, only the monthly price that
    follows the trial (`plan_cost_after_trial_minor`, in the business
    currency; None when priced in another).

    The cabinet's periods never start before the business went live (or
    was created): `is_since_launch` says `date_from` was moved up to that
    day from an earlier one asked for, and `went_live_at` is when it first
    went live (None: not yet, or before milestones were kept).
    """

    business_id: BusinessId
    currency_code: CurrencyCode
    timezone: TimezoneName
    date_from: LocalDate
    date_to: LocalDate
    previous_date_from: LocalDate
    previous_date_to: LocalDate
    value_basis: ValueBasis
    average_check_minor: AverageCheckMinor | None = None
    average_check_source: AverageCheckSource
    typical_check_minor: AverageCheckMinor | None = None
    seconds_per_reply: StaffSecondsPerReply
    seconds_per_call: StaffSecondsPerCall
    current: ValueTotals
    previous: ValueTotals
    plan_cost_minor: PlanCostMinor | None = None
    return_multiple: ValueReturnMultiple | None = None
    is_trial: IsTrialPeriod = False
    trial_ends_at: Microseconds | None = None
    plan_cost_after_trial_minor: MonthlyPlanPriceMinor | None = None
    is_since_launch: IsPeriodSinceLaunch = False
    went_live_at: Microseconds | None = None
