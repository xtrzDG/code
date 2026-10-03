"""Money arithmetic of a client's cost report: usage, shares, rates, margins."""

from collections import defaultdict
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import InvoiceDocument, UsageEventDocument
from app.schemas.dto.billing_ledger import ClientCostQuery, UsageCostLine
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.billing.constrained_floats import GrossMarginPercent
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantityTotal,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.exchange_rates.rate_math import read_rate
from app.utilities.money.money_math import get_currency_minor_unit_digits

PROVIDER_COST_CURRENCY: CurrencyCode = CurrencyCode("USD")
MICRO_UNITS_PER_UNIT: Decimal = Decimal(1_000_000)
ONE_HUNDRED: Decimal = Decimal(100)
MARGIN_PERCENT_STEP: Decimal = Decimal("0.01")
WHOLE_MINOR_UNIT: Decimal = Decimal(1)
LLM_USAGE_KINDS: frozenset[UsageKind] = frozenset(
    {UsageKind.LLM_INPUT_TOKENS, UsageKind.LLM_OUTPUT_TOKENS}
)


def summarize_usage_costs(events: list[UsageEventDocument]) -> list[UsageCostLine]:
    """Quantity and cost per usage kind, in the order of UsageKind."""

    quantities: defaultdict[UsageKind, int] = defaultdict(int)
    costs: defaultdict[UsageKind, int] = defaultdict(int)
    for event in events:
        quantities[event.kind] += int(event.quantity)
        costs[event.kind] += int(event.cost_micro_usd)

    return [
        UsageCostLine(
            kind=kind,
            quantity=UsageQuantityTotal(quantities[kind]),
            cost_micro_usd=CostMicroUsd(costs[kind]),
        )
        for kind in UsageKind
        if kind in quantities
    ]


def compute_period_share(invoice: InvoiceDocument, query: ClientCostQuery) -> Decimal:
    """Share of the invoice's service period inside the query window."""

    period_length: int = int(invoice.period_end) - int(invoice.period_start)
    if period_length <= 0:
        is_inside: bool = query.period_start <= invoice.period_start < query.period_end
        return Decimal(1) if is_inside else Decimal(0)

    overlap: int = min(int(invoice.period_end), int(query.period_end)) - max(
        int(invoice.period_start),
        int(query.period_start),
    )
    if overlap <= 0:
        return Decimal(0)

    return Decimal(overlap) / Decimal(period_length)


def convert_amount(
    amount: Decimal,
    source_currency: CurrencyCode,
    target_currency: CurrencyCode,
    exchange_rate_registry: ExchangeRateRegistryContract,
) -> tuple[Decimal, ExchangeRateQuote | None] | None:
    """
    Convert major units with the registry's rate (published, inverse or a
    cross rate through the euro), exactly. None without a rate.
    """

    if source_currency == target_currency:
        return amount, None

    rate: ExchangeRateQuote | None = exchange_rate_registry.find_rate(
        source_currency,
        target_currency,
    )
    if rate is None:
        return None

    return amount * read_rate(rate.rate_value), rate


def to_minor_units(amount: Decimal, currency_code: CurrencyCode) -> int:
    """Major units -> whole minor units, rounded half to even."""

    digits: int = int(get_currency_minor_unit_digits(currency_code))
    return int(
        amount.scaleb(digits).quantize(WHOLE_MINOR_UNIT, rounding=ROUND_HALF_EVEN)
    )


def compute_margin_percent(
    revenue_minor: int,
    cost_minor: int,
) -> GrossMarginPercent | None:
    """(revenue - cost) / revenue in percent, two decimals; None without revenue."""

    if revenue_minor <= 0:
        return None

    percent: Decimal = (
        (Decimal(revenue_minor - cost_minor) / Decimal(revenue_minor)) * ONE_HUNDRED
    ).quantize(MARGIN_PERCENT_STEP, rounding=ROUND_HALF_UP)
    return GrossMarginPercent(float(percent))
