"""
Prices of a subscription in its currency.

A business pays in its own currency when the price book has both the
monthly price and the setup fee of the plan in it (Georgia: GEL);
otherwise it pays in the plan currency (EUR). Prices are never converted
with exchange rates. The annual price is twelve monthly prices minus the
annual discount, rounded once to the minor unit of the currency.
"""

from decimal import Decimal

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import PlanRegistryContract
from app.schemas.constants.billing import BillingPeriod, PlanKey
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.catalog import ExchangeRateQuote, QuotedMoney
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.booleans import IsPriceEstimated
from app.schemas.typings.billing.constrained_integers import DiscountPercent
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.money.money_formatting import format_money
from app.utilities.money.money_math import (
    build_discount_factor,
    convert_money,
    multiply_money,
)

MONTHS_IN_YEAR: Decimal = Decimal(12)


def select_subscription_currency(
    plan_registry: PlanRegistryContract,
    plan_key: PlanKey,
    business_currency_code: CurrencyCode,
) -> CurrencyCode:
    """Business currency when the price book covers it, else the plan currency."""

    monthly_price: Money | None = plan_registry.find_local_monthly_price(
        plan_key,
        business_currency_code,
    )
    setup_fee: Money | None = plan_registry.find_local_setup_fee(
        plan_key,
        business_currency_code,
    )
    if monthly_price is not None and setup_fee is not None:
        return business_currency_code

    return plan_registry.get(plan_key).monthly_price.currency_code


def find_monthly_price(
    plan_registry: PlanRegistryContract,
    plan_key: PlanKey,
    currency_code: CurrencyCode,
) -> Money:
    """
    Raises:
        ValidationFailedError: the plan has no price in this currency.
    """

    monthly_price: Money | None = plan_registry.find_local_monthly_price(
        plan_key,
        currency_code,
    )
    if monthly_price is None:
        raise ValidationFailedError(
            f"Plan {plan_key.value} has no price in {currency_code}."
        )

    return monthly_price


def compute_annual_price(
    monthly_price: Money,
    annual_discount_percent: DiscountPercent,
) -> Money:
    """12 x monthly x (1 - discount), rounded half up in minor units."""

    return multiply_money(
        monthly_price,
        MONTHS_IN_YEAR * build_discount_factor(annual_discount_percent),
    )


def price_subscription(
    plan_registry: PlanRegistryContract,
    plan_key: PlanKey,
    billing_period: BillingPeriod,
    currency_code: CurrencyCode,
) -> Money:
    """Price of one billing period of the plan in the subscription currency."""

    monthly_price: Money = find_monthly_price(plan_registry, plan_key, currency_code)
    if billing_period is BillingPeriod.MONTHLY:
        return monthly_price

    plan: PlanDefinition = plan_registry.get(plan_key)
    return compute_annual_price(monthly_price, plan.annual_discount_percent)


def price_setup_fee(
    plan_registry: PlanRegistryContract,
    plan_key: PlanKey,
    currency_code: CurrencyCode,
) -> Money:
    """
    Raises:
        ValidationFailedError: the plan has no setup fee in this currency.
    """

    setup_fee: Money | None = plan_registry.find_local_setup_fee(
        plan_key,
        currency_code,
    )
    if setup_fee is None:
        raise ValidationFailedError(
            f"Plan {plan_key.value} has no setup fee in {currency_code}."
        )

    return setup_fee


def price_overage_per_minute(
    plan: PlanDefinition,
    currency_code: CurrencyCode,
    exchange_rate_registry: ExchangeRateRegistryContract,
) -> tuple[Money, IsPriceEstimated]:
    """
    Overage price per minute in the subscription currency.

    The plan sets it in its own currency only (concept: 0.15 EUR,
    "≈ 0.44 GEL"); another currency gets an estimate with the official rate,
    and without a rate the plan currency price is returned unchanged.
    """

    overage_price: Money = plan.overage_price_per_minute
    if overage_price.currency_code == currency_code:
        return overage_price, False

    exchange_rate: ExchangeRateQuote | None = exchange_rate_registry.find_rate(
        overage_price.currency_code,
        currency_code,
    )
    if exchange_rate is None:
        return overage_price, False

    return convert_money(overage_price, exchange_rate.rate, currency_code), True


def quote_money(
    money: Money,
    is_estimated: IsPriceEstimated,
    language: LanguageTag,
) -> QuotedMoney:
    """Money with its text in the reader's language."""

    return QuotedMoney(
        money=money,
        text=format_money(money, language),
        is_estimated=is_estimated,
    )
