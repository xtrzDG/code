from app.contracts.registries import PlanRegistryContract
from app.registries.billing.plan_catalog import (
    LOCAL_MONTHLY_PRICE_BOOK,
    LOCAL_SETUP_FEE_BOOK,
    PLAN_DEFINITIONS,
)
from app.schemas.constants.billing import PlanKey
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class PlanRegistry(PlanRegistryContract):
    """
    The concept's three plans with packages, priced in EUR, and the price
    book of explicit local prices (GEL in Georgia).

    A plan's own currency counts as a price-book currency, so EUR lookups
    return the EUR price. Other currencies return None unless the price book
    has them: prices are never converted here.
    """

    def __init__(self) -> None:
        self._plans_by_key: dict[PlanKey, PlanDefinition] = {
            plan.key: plan for plan in PLAN_DEFINITIONS
        }

    def get(self, plan_key: PlanKey) -> PlanDefinition:
        plan: PlanDefinition | None = self._plans_by_key.get(plan_key)
        if plan is None:
            raise NotFoundError(f"Plan {plan_key} is not offered.")

        return plan.model_copy(deep=True)

    def list_all(self) -> list[PlanDefinition]:
        return [
            self._plans_by_key[plan_key].model_copy(deep=True)
            for plan_key in PlanKey
            if plan_key in self._plans_by_key
        ]

    def find_local_monthly_price(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        return find_price_book_price(
            self.get(plan_key).monthly_price,
            LOCAL_MONTHLY_PRICE_BOOK.get(plan_key, ()),
            currency_code,
        )

    def find_local_setup_fee(
        self,
        plan_key: PlanKey,
        currency_code: CurrencyCode,
    ) -> Money | None:
        return find_price_book_price(
            self.get(plan_key).setup_fee,
            LOCAL_SETUP_FEE_BOOK.get(plan_key, ()),
            currency_code,
        )


def find_price_book_price(
    base_price: Money,
    local_prices: tuple[Money, ...],
    currency_code: CurrencyCode,
) -> Money | None:
    if base_price.currency_code == currency_code:
        return base_price

    for local_price in local_prices:
        if local_price.currency_code == currency_code:
            return local_price

    return None
