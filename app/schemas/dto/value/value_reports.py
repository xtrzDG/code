"""The cabinet's Reports page: stored monthly reports and digests."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.value import (
    AverageCheckSource,
    ValueBasis,
    ValueReportDelivery,
    ValueReportKind,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.value.value_model import ValueTotals
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_floats import ValueReturnMultiple
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    DigestRecipientCount,
    PlanCostMinor,
)
from app.schemas.typings.value.constrained_strings import ValueReportPeriodKey
from app.schemas.typings.value.prefixed_id import ValueReportId


class ValueReportPageQuery(ImmutableDTO):
    """One page of a business's reports of a kind (monthly by default)."""

    user_id: UserId
    business_id: BusinessId
    kind: ValueReportKind = ValueReportKind.MONTHLY
    page: PageRequest = Field(default_factory=PageRequest)


class ValueReportQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    report_id: ValueReportId


class ValueReportView(ImmutableDTO):
    """
    One stored report: its period and the one before, the totals of both as
    they were when it was made, the average check it used, what the plan
    cost for the period and how many times the money covered it (None:
    reports from before, or a plan in another currency), and whether it
    went out (`delivery`, to `recipient_count` addresses and devices).
    """

    id: ValueReportId
    business_id: BusinessId
    kind: ValueReportKind
    period_key: ValueReportPeriodKey
    date_from: LocalDate
    date_to: LocalDate
    previous_date_from: LocalDate
    previous_date_to: LocalDate
    currency_code: CurrencyCode
    value_basis: ValueBasis
    average_check_minor: AverageCheckMinor | None = None
    average_check_source: AverageCheckSource
    current: ValueTotals
    previous: ValueTotals
    delivery: ValueReportDelivery
    recipient_count: DigestRecipientCount
    plan_cost_minor: PlanCostMinor | None = None
    return_multiple: ValueReturnMultiple | None = None
    created_at: Microseconds


class ValueReportPage(ImmutableDTO):
    """Reports newest period first; `next_cursor` is None on the last page."""

    items: list[ValueReportView] = Field(default_factory=list[ValueReportView])
    next_cursor: PageCursor | None = None
