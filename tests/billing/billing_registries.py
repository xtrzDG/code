"""Registries the billing tests swap in: a fixed price book and static rates."""

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import PlanRegistryContract
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.catalog.plan_quotes import ExchangeRateQuote
from app.schemas.typings.billing.constrained_floats import ExchangeRate
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.constrained_strings import ExchangeRateDate
from app.schemas.typings.billing.strings import ExchangeRateSourceName
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class PriceBookPlanRegistry(PlanRegistryContract):
    """
    The real plans with an extra price book, e.g. yen prices for Japan or
    odd amounts that exercise rounding.
    """

    def __init__(
        self,
        monthly_prices: dict[tuple[PlanKey, str], int],
        setup_fees: dict[tuple[PlanKey, str], int] | None = None,
    ) -> None:
        self._plans = PlanRegistry()
        self._monthly_prices: dict[tuple[PlanKey, str], int] = monthly_prices
        self._setup_fees: dict[tuple[PlanKey, str], int] = setup_fees or {}

    def get(self, plan_key: PlanKey) -> PlanDefinition:
        return self._plans.get(plan_key)

    def list_all(self) -> list[PlanDefinition]:
        return self._plans.list_all()

    def find_local_monthly_price(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        amount: int | None = self._monthly_prices.get((plan_key, str(currency_code)))
        if amount is None:
            return self._plans.find_local_monthly_price(plan_key, currency_code)

        return Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency_code)

    def find_local_setup_fee(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        amount: int | None = self._setup_fees.get((plan_key, str(currency_code)))
        if amount is None:
            return self._plans.find_local_setup_fee(plan_key, currency_code)

        return Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency_code)


class StaticExchangeRateRegistry(ExchangeRateRegistryContract):
    """Official rates given by the test."""

    def __init__(self, rates: list[tuple[str, str, float]]) -> None:
        self._quotes: list[ExchangeRateQuote] = [
            ExchangeRateQuote(
                base_currency_code=CurrencyCode(base),
                quote_currency_code=CurrencyCode(quote),
                rate=ExchangeRate(rate),
                rate_date=ExchangeRateDate("2026-09-30"),
                source=ExchangeRateSourceName("Test central bank"),
            )
            for base, quote, rate in rates
        ]

    def find_rate(
        self,
        base_currency_code: CurrencyCode,
        quote_currency_code: CurrencyCode,
    ) -> ExchangeRateQuote | None:
        for quote in self._quotes:
            if (
                quote.base_currency_code == base_currency_code
                and quote.quote_currency_code == quote_currency_code
            ):
                return quote

        return None

    def list_all(self) -> list[ExchangeRateQuote]:
        return list(self._quotes)
