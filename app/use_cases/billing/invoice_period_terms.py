"""
What the invoice of a service period charges and covers: a regular period
at the subscription price for its billing period, or one month of a
seasonal pause at its share of the monthly price; and how its line reads.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import InvoiceKind
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.billing_ledger import DueInvoicesRequest, InvoiceDescriptionInput
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.utilities.billing.billing_periods import (
    add_billing_period,
    add_calendar_months,
)
from app.utilities.billing.pause_pricing import pause_month_price_minor

PAUSE_PERIOD_MONTHS: int = 1


def period_price(input_data: DueInvoicesRequest) -> MoneyAmountMinor:
    """The period's price before tax, discount and credit."""

    if input_data.pause_price_percent is None:
        return input_data.subscription.price_minor

    return MoneyAmountMinor(
        pause_month_price_minor(
            input_data.subscription, int(input_data.pause_price_percent)
        )
    )


def period_end(input_data: DueInvoicesRequest) -> Microseconds:
    """The end of the period starting at `period_start` (a pause: one month)."""

    if input_data.pause_price_percent is not None:
        return add_calendar_months(
            input_data.period_start,
            PAUSE_PERIOD_MONTHS,
            input_data.business.timezone,
        )

    return add_billing_period(
        input_data.period_start,
        input_data.subscription.billing_period,
        input_data.business.timezone,
    )


def describe_line(
    input_data: DueInvoicesRequest,
    plan: PlanDefinition,
    kind: InvoiceKind,
    start: Microseconds,
    end: Microseconds,
) -> InvoiceDescriptionInput:
    """What the line is about: worded in the owner language and in each
    language of the PDFs."""

    return InvoiceDescriptionInput(
        kind=kind,
        language=input_data.business.owner_language,
        timezone=input_data.business.timezone,
        plan_names=plan.names,
        billing_period=input_data.subscription.billing_period,
        period_start=start,
        period_end=end,
        is_pause_period=(
            kind is InvoiceKind.SERVICE_PERIOD
            and input_data.pause_price_percent is not None
        ),
    )
