"""
Catalog DTOs: countries, languages, plan quotes, phone parsing and call
forwarding instructions for businesses in any country.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.localization import (
    CallForwardingCondition,
    CountryOnboardingStatus,
    TextDirection,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.localization import (
    CountryProfile,
    LanguageProfile,
    LocalizedText,
)
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
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCode,
    CallForwardingDialCodeTemplate,
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    CarrierName,
    CountryDisplayName,
    CurrencyDisplayName,
    FormattedMoneyText,
    FormattedPhoneNumber,
    InstructionText,
    LanguageDisplayName,
    LocalizedTextValue,
    RawPhoneNumberInput,
    TimezoneDisplayName,
)
from app.schemas.typings.users.prefixed_id import UserId


class ParsePhoneNumberRequest(ImmutableDTO):
    """
    A phone number as typed, with the country to read national formats in.

    Example: {"raw_phone_number": "8 (999) 123-45-67", "country_hint": "RU"}.
    """

    raw_phone_number: RawPhoneNumberInput
    country_hint: CountryCode | None = None


class CountryListRequest(ImmutableDTO):
    """Every country with names in the display language."""

    display_language: LanguageTag


class CountryListItem(ImmutableDTO):
    """Summary of one country for a country picker."""

    country_code: CountryCode
    display_name: CountryDisplayName
    english_name: CountryDisplayName
    calling_code: CountryCallingCode
    currency_code: CurrencyCode
    default_timezone: TimezoneName
    default_owner_language: LanguageTag
    onboarding_status: CountryOnboardingStatus


class CountryList(ImmutableDTO):
    """Countries ordered by their name in the display language."""

    display_language: LanguageTag
    countries: list[CountryListItem]


class CountryProfileRequest(ImmutableDTO):
    """One country's defaults, described in the display language."""

    country_code: CountryCode
    display_language: LanguageTag


class LanguageOption(ImmutableDTO):
    """A language as a picker shows it: in the display language and natively."""

    tag: LanguageTag
    display_name: LanguageDisplayName
    native_name: LanguageDisplayName
    direction: TextDirection


class TimezoneOption(ImmutableDTO):
    """An IANA time zone with its current UTC offset."""

    name: TimezoneName
    display_name: TimezoneDisplayName


class CountryProfileView(ImmutableDTO):
    """A country profile with every code rendered for people."""

    profile: CountryProfile
    display_language: LanguageTag
    display_name: CountryDisplayName
    currency_display_name: CurrencyDisplayName
    timezones: list[TimezoneOption]
    default_timezone: TimezoneOption
    default_customer_languages: list[LanguageOption]
    on_request_customer_languages: list[LanguageOption]
    default_owner_language: LanguageOption


class LanguageListRequest(ImmutableDTO):
    """Every listed language with names in the display language."""

    display_language: LanguageTag


class LanguageListItem(ImmutableDTO):
    """A language profile with its name in the display language."""

    profile: LanguageProfile
    display_name: LanguageDisplayName


class LanguageList(ImmutableDTO):
    """Languages ordered by their name in the display language."""

    display_language: LanguageTag
    languages: list[LanguageListItem]


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


class CallForwardingCodeTemplate(ImmutableDTO):
    """A forwarding code before the assistant's number is filled in."""

    condition: CallForwardingCondition
    dial_code_template: CallForwardingDialCodeTemplate
    descriptions: LocalizedText


class CarrierForwardingGuide(ImmutableDTO):
    """Forwarding codes of one named mobile carrier."""

    carrier_name: CarrierName
    code_templates: list[CallForwardingCodeTemplate]
    notes: LocalizedText | None = None


class CallForwardingGuide(ImmutableDTO):
    """
    How owners in one country forward unanswered calls to the assistant.

    Step and note texts are templates with the placeholders {number},
    {no_answer_code}, {busy_code}, {unreachable_code} and {cancel_code}.
    """

    country_code: CountryCode
    code_templates: list[CallForwardingCodeTemplate]
    carriers: list[CarrierForwardingGuide] = Field(
        default_factory=list[CarrierForwardingGuide]
    )
    steps: list[LocalizedText]
    notes: list[LocalizedText] = Field(default_factory=list[LocalizedText])


class CallForwardingInstructionsRequest(ImmutableDTO):
    """
    Cabinet request for forwarding instructions.

    Without a display language the owner language of the business is used.
    """

    user_id: UserId
    business_id: BusinessId
    display_language: LanguageTag | None = None


class CallForwardingInstructionsQuery(ImmutableDTO):
    """Forwarding instructions for a business the caller may act on."""

    business: BusinessDocument
    display_language: LanguageTag


class CallForwardingCode(ImmutableDTO):
    """A ready-to-dial forwarding code."""

    condition: CallForwardingCondition
    dial_code: CallForwardingDialCode
    description: InstructionText


class CarrierForwardingInstructions(ImmutableDTO):
    """Ready-to-dial codes of one named mobile carrier."""

    carrier_name: CarrierName
    codes: list[CallForwardingCode]
    note: InstructionText | None = None


class CallForwardingInstructions(ImmutableDTO):
    """
    Step-by-step forwarding of "no answer / busy / unreachable" calls from the
    venue's phone to the assistant's number (concept section 6).

    Texts are in the display language when available, else in English.
    """

    business_id: BusinessId
    country_code: CountryCode
    display_language: LanguageTag
    assistant_phone_number: E164PhoneNumber
    assistant_phone_number_display: FormattedPhoneNumber
    codes: list[CallForwardingCode]
    carriers: list[CarrierForwardingInstructions] = Field(
        default_factory=list[CarrierForwardingInstructions]
    )
    steps: list[InstructionText]
    notes: list[InstructionText] = Field(default_factory=list[InstructionText])
