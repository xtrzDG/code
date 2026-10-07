"""Registries the billing tests swap in: a fixed price book and static rates."""

from app.contracts.registries import PlanRegistryContract
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import PlanKey, SetupOption
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from tests.billing.exchange_rate_fixtures import rate_registry


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

    def find_setup_fee(
        self,
        plan_key: PlanKey,
        option: SetupOption,
        currency_code: CurrencyCode,
    ) -> Money | None:
        if option is SetupOption.DONE_FOR_YOU:
            return self.find_local_setup_fee(plan_key, currency_code)

        return self._plans.find_setup_fee(plan_key, option, currency_code)


def static_rate_registry(rates: list[tuple[str, str, str]]) -> ExchangeRateRegistry:
    """
    The real registry over only the rates the test gives (dated today, no
    catalog fallback): inverses and euro cross rates still apply.
    """

    return rate_registry(rates, fallback=())
