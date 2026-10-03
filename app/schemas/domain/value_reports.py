from base_pydantic_schemas import BaseDocument, PersistentDocument
from typed_time_provider import Microseconds

from app.schemas.constants.value import (
    AverageCheckSource,
    ValueBasis,
    ValueReportDelivery,
    ValueReportKind,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    DigestRecipientCount,
    EstimatedRevenueMinor,
    StaffMinutesSaved,
)
from app.schemas.typings.value.constrained_strings import ValueReportPeriodKey
from app.schemas.typings.value.prefixed_id import ValueReportId


class ValueTotalsSnapshot(PersistentDocument):
    """
    What the assistant did in one period, as a report stored it: the
    counts of the value model and the money estimate (None when no
    average check was known). Sandbox activity is never counted.
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


class ValueReportDocument(BaseDocument):
    """
    One summary of the value the assistant brought a business (a daily or
    weekly digest, or a monthly report), stored once per business, kind
    and period (the id derives from them), so the job that sends it never
    sends a period twice, also across restarts and workers.

    The period (`date_from` to `date_to`, local dates, inclusive) is
    compared with the one before it. The totals are a snapshot: later
    changes (a booking cancelled next week) do not rewrite a sent report.
    `starts_at` (UTC microseconds of the first local day) orders the
    reports of a business. `delivery` and `recipient_count` say whether
    it went out.
    """

    id: ValueReportId
    business_id: BusinessId
    kind: ValueReportKind
    period_key: ValueReportPeriodKey
    date_from: LocalDate
    date_to: LocalDate
    previous_date_from: LocalDate
    previous_date_to: LocalDate
    starts_at: Microseconds
    currency_code: CurrencyCode
    value_basis: ValueBasis
    average_check_minor: AverageCheckMinor | None = None
    average_check_source: AverageCheckSource
    current: ValueTotalsSnapshot
    previous: ValueTotalsSnapshot
    delivery: ValueReportDelivery
    recipient_count: DigestRecipientCount
