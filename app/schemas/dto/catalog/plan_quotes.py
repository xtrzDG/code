"""Plan quotes in the currency of a country, with the exchange rate used."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.booleans import IsPriceEstimated
from app.schemas.typings.billing.constrained_floats import ExchangeRate
from app.schemas.typings.billing.constrained_integers import (
    DiscountPercent,
    GracePeriodDays,
    IncludedDialogs,
    IncludedVoiceMinutes,
    TrialDays,
)
from app.schemas.typings.billing.constrained_strings import ExchangeRateDate
from app.schemas.typings.billing.strings import ExchangeRateSourceName
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    FormattedMoneyText,
    LocalizedTextValue,
)


class ExchangeRateQuote(ImmutableDTO):
    """
    An official rate: `rate` units of the quote currency for one base unit.

    Example: EUR -> GEL 2.9552, National Bank of Georgia, 2026-09-30.
    """

    base_currency_code: CurrencyCode
    quote_currency_code: CurrencyCode
    rate: ExchangeRate
    rate_date: ExchangeRateDate
    source: ExchangeRateSourceName


class PlanQuoteRequest(ImmutableDTO):
    """Plans priced for a business in a country, described in a language."""

    country_code: CountryCode
    display_language: LanguageTag


class QuotedMoney(ImmutableDTO):
    """
    A price and its text in the display language.

    `is_estimated` marks a conversion by an exchange rate rather than a price
    from the price book; the owner is charged the price-book amount.
    """

    money: Money
    text: FormattedMoneyText
    is_estimated: IsPriceEstimated = False


class PlanQuote(ImmutableDTO):
    """
    One plan priced in EUR and, when known, in the country's currency.

    `annual_price` is the price of twelve months with the annual discount.
    Local prices are None when neither the price book nor an official rate
    knows the currency: prices are never invented.
    """

    plan_key: PlanKey
    name: LocalizedTextValue
    description: LocalizedTextValue
    included_voice_minutes: IncludedVoiceMinutes
    included_dialogs: IncludedDialogs
    channels: list[ChannelKind]
    is_voice_included: IsVoiceEnabled
    trial_days: TrialDays
    grace_period_days: GracePeriodDays
    annual_discount_percent: DiscountPercent
    monthly_price: QuotedMoney
    annual_price: QuotedMoney
    setup_fee: QuotedMoney
    overage_price_per_minute: QuotedMoney
    local_monthly_price: QuotedMoney | None = None
    local_annual_price: QuotedMoney | None = None
    local_setup_fee: QuotedMoney | None = None
    local_overage_price_per_minute: QuotedMoney | None = None


class PlanQuoteList(ImmutableDTO):
    """
    Every plan for one country.

    `exchange_rate` is the rate behind estimated local prices, if any were
    estimated.
    """

    country_code: CountryCode
    display_language: LanguageTag
    local_currency_code: CurrencyCode
    exchange_rate: ExchangeRateQuote | None = None
    quotes: list[PlanQuote]
