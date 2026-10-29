"""
Planned monthly provider cost of a typical client per plan (concept
"Себестоимость одного клиента в месяц"): Chat 20 EUR, Voice + chat
54.90 EUR, Plus 154.40 EUR. The admin compares the actual cost with it,
and the spend guard's default daily limits are multiples of its daily
share (`spend_limit_defaults`).
"""

from app.schemas.constants.billing import PlanKey
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode

PLANNED_COST_CURRENCY: CurrencyCode = CurrencyCode("EUR")
PLANNED_MONTHLY_PROVIDER_COSTS: dict[PlanKey, Money] = {
    PlanKey.CHAT: Money(
        amount_minor=MoneyAmountMinor(2000),
        currency_code=PLANNED_COST_CURRENCY,
    ),
    PlanKey.VOICE_AND_CHAT: Money(
        amount_minor=MoneyAmountMinor(5490),
        currency_code=PLANNED_COST_CURRENCY,
    ),
    PlanKey.PLUS: Money(
        amount_minor=MoneyAmountMinor(15440),
        currency_code=PLANNED_COST_CURRENCY,
    ),
}
