"""
A business's daily spend limits: its own (set by the platform team) or its
plan's defaults, multiples of the plan's planned daily provider cost.

The planned monthly cost of a plan (`planned_provider_costs`, EUR) over 30
days is what a typical client of the plan costs in a day; the soft limit
is SPEND_SOFT_LIMIT_MULTIPLE times that (5 by default), the hard one
SPEND_HARD_LIMIT_MULTIPLE times (15). Chat: about $3.6 and $10.8 a day.
Usage is priced in US dollars, so the planned cost is converted with the
newest EUR -> USD rate; without one it counts one dollar per euro.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.billing import PlanKey
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.spend_guard import SpendLimits
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.spend.constrained_integers import DailySpendLimitMicroUsd
from app.utilities.billing.client_cost_math import convert_amount
from app.utilities.billing.planned_provider_costs import (
    PLANNED_MONTHLY_PROVIDER_COSTS,
)
from app.utilities.money.money_math import get_currency_minor_unit_digits

DAYS_PER_PLANNED_MONTH: int = 30
MICRO_USD_PER_USD: Decimal = Decimal(1_000_000)
SPEND_CURRENCY: CurrencyCode = CurrencyCode("USD")


def planned_daily_cost_micro_usd(
    plan_key: PlanKey, exchange_rate_registry: ExchangeRateRegistryContract
) -> int:
    """The plan's planned daily provider cost in micro-USD (Chat's for others)."""

    monthly: Money = PLANNED_MONTHLY_PROVIDER_COSTS.get(
        plan_key, PLANNED_MONTHLY_PROVIDER_COSTS[PlanKey.CHAT]
    )
    major: Decimal = Decimal(int(monthly.amount_minor)).scaleb(
        -int(get_currency_minor_unit_digits(monthly.currency_code))
    )
    converted = convert_amount(
        major, monthly.currency_code, SPEND_CURRENCY, exchange_rate_registry
    )
    usd: Decimal = major if converted is None else converted[0]
    return int(
        (usd * MICRO_USD_PER_USD / DAYS_PER_PLANNED_MONTH).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


def resolve_spend_limits(
    limits: BusinessLimitsDocument,
    plan_key: PlanKey,
    settings: SpendGuardSettings,
    exchange_rate_registry: ExchangeRateRegistryContract,
) -> SpendLimits:
    """
    The business's own limits where the team set them, the plan's defaults
    otherwise; a soft limit above the hard one is held at the hard one.
    """

    daily: int = planned_daily_cost_micro_usd(plan_key, exchange_rate_registry)
    hard: int = (
        daily * int(settings.hard_limit_multiple)
        if limits.daily_hard_limit_micro_usd is None
        else int(limits.daily_hard_limit_micro_usd)
    )
    soft: int = (
        daily * int(settings.soft_limit_multiple)
        if limits.daily_soft_limit_micro_usd is None
        else int(limits.daily_soft_limit_micro_usd)
    )
    return SpendLimits(
        soft_limit_micro_usd=DailySpendLimitMicroUsd(min(soft, hard)),
        hard_limit_micro_usd=DailySpendLimitMicroUsd(hard),
        is_custom=(
            limits.daily_soft_limit_micro_usd is not None
            or limits.daily_hard_limit_micro_usd is not None
        ),
    )
