"""
The value model: what the assistant did for a business in a period and
what that is worth, next to the period just before it. One computation
serves the dashboard, the digests and the monthly report.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.value import AverageCheckSource, ValueBasis
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    TimezoneName,
)
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    EstimatedRevenueMinor,
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
    - the money estimate: the assistant's bookings (or, for niches that
      take orders instead, its requests) times the average check; None
      without an average check.
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


class ValueModel(ImmutableDTO):
    """
    The value of a business in a period and the period before it, in the
    business currency and time zone. `average_check_minor` is the owner's
    (`OWNER`) or the niche's typical check in the business currency
    (`NICHE_DEFAULT`, also given as `typical_check_minor`); without either
    there is no money estimate. The staff time rates explain the minutes.
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
