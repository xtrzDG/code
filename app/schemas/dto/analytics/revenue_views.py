"""Recurring revenue, its movements, ARPA and gross margin, in euros."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.analytics import MrrMovementKind
from app.schemas.dto.billing import Money
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.analytics.constrained_integers import AccountCount
from app.schemas.typings.analytics.integers import MrrChangeMinor
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class MrrMovementView(ImmutableDTO):
    """
    How much monthly recurring revenue moved one way in the period, and
    across how many businesses (each counted once per kind).
    """

    kind: MrrMovementKind
    amount: Money
    accounts: AccountCount


class MrrView(ImmutableDTO):
    """
    Monthly recurring revenue at the start and the end of the period and
    the movements between (start + new + reactivation + expansion -
    contraction - churn = end), the paying accounts at the end and the
    average revenue per account. Subscriptions in a currency without an
    official rate to euros are left out and named; `rates` are the rates
    the others were converted with (their source and date), so the page
    can name them truthfully.
    """

    start: Money
    end: Money
    net_change: MrrChangeMinor
    movements: list[MrrMovementView]
    paying_accounts: AccountCount
    arpa: Money | None = None
    unconverted_currencies: list[CurrencyCode]
    rates: list[ExchangeRateQuote] = Field(default_factory=list[ExchangeRateQuote])


class MarginView(ImmutableDTO):
    """
    Revenue and provider cost of the period over the businesses in scope
    (the admin's client cost report, in euros) and the gross margin.
    """

    revenue: Money
    provider_cost: Money
    gross_margin_percent: GrossMarginPercent | None = None
    accounts: AccountCount
    accounts_without_rate: AccountCount


class RevenueView(ImmutableDTO):
    mrr: MrrView
    margin: MarginView
