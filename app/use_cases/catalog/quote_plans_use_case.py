from decimal import Decimal

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import CountryRegistryContract, PlanRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.catalog.plan_quotes import (
    ExchangeRateQuote,
    PlanQuote,
    PlanQuoteList,
    PlanQuoteRequest,
    QuotedMoney,
)
from app.schemas.dto.localization import CountryProfile
from app.schemas.typings.billing.booleans import IsPriceEstimated
from app.schemas.typings.billing.constrained_integers import DiscountPercent
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.money.money_formatting import format_money
from app.utilities.money.money_math import (
    build_discount_factor,
    convert_money,
    multiply_money,
)

MONTHS_IN_YEAR: Decimal = Decimal(12)


class QuotePlansUseCase(UseCaseContract[PlanQuoteRequest, PlanQuoteList]):
    """
    Price every plan for a business in a country, in the display language.

    EUR prices always come from the plan. The local currency of the country
    is priced from the price book first (Georgia: 293 / 517 / 1 031 GEL);
    without a price-book entry an official exchange rate gives an estimate
    marked `is_estimated`; without either the local price stays empty, so
    no price is ever invented. The annual price is twelve months minus the
    annual discount.
    """

    def __init__(
        self,
        plan_registry: PlanRegistryContract,
        country_registry: CountryRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._plan_registry: PlanRegistryContract = plan_registry
        self._country_registry: CountryRegistryContract = country_registry
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(self, input_data: PlanQuoteRequest) -> PlanQuoteList:
        require_babel_locale(input_data.display_language)
        country: CountryProfile = self._country_registry.get(input_data.country_code)
        quotes: list[PlanQuote] = []
        used_exchange_rate: ExchangeRateQuote | None = None
        for plan in self._plan_registry.list_all():
            quote, plan_exchange_rate = self._quote_plan(
                plan,
                country.currency_code,
                input_data.display_language,
            )
            quotes.append(quote)
            if plan_exchange_rate is not None:
                used_exchange_rate = plan_exchange_rate

        return PlanQuoteList(
            country_code=country.country_code,
            display_language=input_data.display_language,
            local_currency_code=country.currency_code,
            exchange_rate=used_exchange_rate,
            quotes=quotes,
        )

    def _quote_plan(
        self,
        plan: PlanDefinition,
        local_currency_code: CurrencyCode,
        display_language: LanguageTag,
    ) -> tuple[PlanQuote, ExchangeRateQuote | None]:
        exchange_rate: ExchangeRateQuote | None = None
        if plan.monthly_price.currency_code != local_currency_code:
            exchange_rate = self._exchange_rate_registry.find_rate(
                plan.monthly_price.currency_code,
                local_currency_code,
            )

        local_monthly_price: QuotedMoney | None = price_locally(
            plan.monthly_price,
            self._plan_registry.find_local_monthly_price(plan.key, local_currency_code),
            exchange_rate,
            display_language,
        )
        local_setup_fee: QuotedMoney | None = price_locally(
            plan.setup_fee,
            self._plan_registry.find_local_setup_fee(plan.key, local_currency_code),
            exchange_rate,
            display_language,
        )
        local_overage_price: QuotedMoney | None = price_locally(
            plan.overage_price_per_minute,
            (
                plan.overage_price_per_minute
                if plan.overage_price_per_minute.currency_code == local_currency_code
                else None
            ),
            exchange_rate,
            display_language,
        )
        is_rate_used: bool = any(
            quoted_money is not None and quoted_money.is_estimated
            for quoted_money in (
                local_monthly_price,
                local_setup_fee,
                local_overage_price,
            )
        )
        quote = PlanQuote(
            plan_key=plan.key,
            name=self._localized_text_resolver.resolve(plan.names, display_language),
            description=self._localized_text_resolver.resolve(
                plan.descriptions,
                display_language,
            ),
            included_voice_minutes=plan.included_voice_minutes,
            included_dialogs=plan.included_dialogs,
            channels=list(plan.channels),
            is_voice_included=plan.is_voice_included,
            trial_days=plan.trial_days,
            grace_period_days=plan.grace_period_days,
            annual_discount_percent=plan.annual_discount_percent,
            monthly_price=quote_money(plan.monthly_price, False, display_language),
            annual_price=quote_annual_price(
                quote_money(plan.monthly_price, False, display_language),
                plan.annual_discount_percent,
                display_language,
            ),
            setup_fee=quote_money(plan.setup_fee, False, display_language),
            overage_price_per_minute=quote_money(
                plan.overage_price_per_minute,
                False,
                display_language,
            ),
            local_monthly_price=local_monthly_price,
            local_annual_price=(
                quote_annual_price(
                    local_monthly_price,
                    plan.annual_discount_percent,
                    display_language,
                )
                if local_monthly_price is not None
                else None
            ),
            local_setup_fee=local_setup_fee,
            local_overage_price_per_minute=local_overage_price,
        )
        return quote, exchange_rate if is_rate_used else None


def price_locally(
    base_price: Money,
    price_book_price: Money | None,
    exchange_rate: ExchangeRateQuote | None,
    display_language: LanguageTag,
) -> QuotedMoney | None:
    """Price-book price, else a conversion marked as estimated, else None."""

    if price_book_price is not None:
        return quote_money(price_book_price, False, display_language)

    if exchange_rate is None or exchange_rate.base_currency_code != (
        base_price.currency_code
    ):
        return None

    return quote_money(
        convert_money(
            base_price,
            exchange_rate.rate_value,
            exchange_rate.quote_currency_code,
        ),
        True,
        display_language,
    )


def quote_annual_price(
    monthly_price: QuotedMoney,
    annual_discount_percent: DiscountPercent,
    display_language: LanguageTag,
) -> QuotedMoney:
    return quote_money(
        multiply_money(
            monthly_price.money,
            MONTHS_IN_YEAR * build_discount_factor(annual_discount_percent),
        ),
        monthly_price.is_estimated,
        display_language,
    )


def quote_money(
    money: Money,
    is_estimated: IsPriceEstimated,
    display_language: LanguageTag,
) -> QuotedMoney:
    return QuotedMoney(
        money=money,
        text=format_money(money, display_language),
        is_estimated=is_estimated,
    )
