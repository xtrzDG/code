"""
A plan quote as one location of a brand pays it (pure; R17 billing):
the additional-location price a month for a further location, and no
setup fee where another location carries the brand's one fee. Mirrors
how subscriptions are priced (`app/use_cases/shared/subscription_pricing.py`)
so the cabinet quotes the price that is billed.
"""

from decimal import Decimal

from app.schemas.constants.billing import SetupOption
from app.schemas.dto.billing import Money
from app.schemas.dto.catalog.plan_quotes import (
    PlanQuote,
    QuotedMoney,
    SetupOptionQuote,
)
from app.schemas.typings.billing.constrained_integers import (
    DiscountPercent,
    MoneyAmountMinor,
)
from app.schemas.typings.brands.booleans import (
    IsAdditionalLocation,
    IsBrandSetupFeeCovered,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.money.money_formatting import format_money
from app.utilities.money.money_math import build_discount_factor, multiply_money

MONTHS_IN_YEAR: Decimal = Decimal(12)


def price_for_location(
    quote: PlanQuote,
    is_additional_location: IsAdditionalLocation,
    is_setup_fee_covered: IsBrandSetupFeeCovered,
    display_language: LanguageTag,
) -> PlanQuote:
    """The quote with the location's monthly, annual and setup prices."""

    priced: PlanQuote = quote
    if is_additional_location:
        priced = priced_as_further_location(priced, display_language)

    if is_setup_fee_covered:
        priced = without_setup_fee(priced, display_language)

    return priced


def priced_as_further_location(
    quote: PlanQuote, display_language: LanguageTag
) -> PlanQuote:
    """
    The additional-location price a month, in the plan currency and
    locally. A local additional price that is only an estimate while the
    price book has the plan's local price is not what is billed (a
    currency without its own additional-location price bills the plan
    price), so the local plan price stays.
    """

    local: QuotedMoney | None = quote.local_additional_location_price
    if local is None or (
        local.is_estimated
        and quote.local_monthly_price is not None
        and not quote.local_monthly_price.is_estimated
    ):
        local = quote.local_monthly_price

    return quote.model_copy(
        update={
            "monthly_price": quote.additional_location_price,
            "annual_price": annual_of(
                quote.additional_location_price,
                quote.annual_discount_percent,
                display_language,
            ),
            "local_monthly_price": local,
            "local_annual_price": (
                None
                if local is None
                else annual_of(local, quote.annual_discount_percent, display_language)
            ),
        }
    )


def without_setup_fee(quote: PlanQuote, display_language: LanguageTag) -> PlanQuote:
    """No setup fee in any currency: another location carries the brand's."""

    return quote.model_copy(
        update={
            "setup_fee": free_of(quote.setup_fee, display_language),
            "local_setup_fee": (
                None
                if quote.local_setup_fee is None
                else free_of(quote.local_setup_fee, display_language)
            ),
            "setup_options": [
                free_option(option, display_language) for option in quote.setup_options
            ],
        }
    )


def free_option(
    option: SetupOptionQuote, display_language: LanguageTag
) -> SetupOptionQuote:
    if option.option is not SetupOption.DONE_FOR_YOU:
        return option

    return option.model_copy(
        update={
            "fee": free_of(option.fee, display_language),
            "local_fee": (
                None
                if option.local_fee is None
                else free_of(option.local_fee, display_language)
            ),
        }
    )


def annual_of(
    monthly: QuotedMoney,
    annual_discount_percent: DiscountPercent,
    display_language: LanguageTag,
) -> QuotedMoney:
    """Twelve months minus the annual discount, rounded once."""

    annual: Money = multiply_money(
        monthly.money,
        MONTHS_IN_YEAR * build_discount_factor(annual_discount_percent),
    )
    return QuotedMoney(
        money=annual,
        text=format_money(annual, display_language),
        is_estimated=monthly.is_estimated,
    )


def free_of(price: QuotedMoney, display_language: LanguageTag) -> QuotedMoney:
    """Nothing, in the price's currency."""

    free: Money = Money(
        amount_minor=MoneyAmountMinor(0), currency_code=price.money.currency_code
    )
    return QuotedMoney(
        money=free,
        text=format_money(free, display_language),
        is_estimated=False,
    )
