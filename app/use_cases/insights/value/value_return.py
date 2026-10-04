"""
What the assistant returned against its price: the money estimate of a
period divided by what the business's plan costs for the same days
("≈ 3.7× the plan price"). Only in the business currency: a plan paid in
another currency is never converted, so it gives no multiple.
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.schemas.constants.billing import BillingPeriod
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_floats import ValueReturnMultiple
from app.schemas.typings.value.constrained_integers import (
    EstimatedRevenueMinor,
    PlanCostMinor,
)
from app.use_cases.shared.billing_records import find_current_subscription

MONTHS_IN_YEAR: int = 12
# The average Gregorian month, for periods that are not one calendar month.
AVERAGE_MONTH_DAYS: Decimal = Decimal("30.436875")
MULTIPLE_STEP: Decimal = Decimal("0.1")


@dataclass(frozen=True)
class PlanPrices:
    """Where a business's monthly plan price is read from."""

    subscription_repo: SubscriptionRepoContract
    plan_registry: PlanRegistryContract


@dataclass(frozen=True)
class PlanReturn:
    """The plan's cost for a period and the multiple the money made of it."""

    plan_cost_minor: PlanCostMinor | None = None
    return_multiple: ValueReturnMultiple | None = None


NO_RETURN: PlanReturn = PlanReturn()


def monthly_plan_price(prices: PlanPrices, business: BusinessDocument) -> Money | None:
    """
    What the business pays a month: its subscription's price (an annual one
    spread over twelve months), else its plan's price in its own currency
    (a business still setting up).
    """

    subscription: SubscriptionDocument | None = find_current_subscription(
        prices.subscription_repo, business.id
    )
    if subscription is not None:
        months: int = (
            1
            if subscription.billing_period is BillingPeriod.MONTHLY
            else MONTHS_IN_YEAR
        )
        return Money.model_validate(
            {
                "amount_minor": round_half_up(
                    Decimal(int(subscription.price_minor)) / months
                ),
                "currency_code": subscription.currency_code,
            }
        )

    local: Money | None = prices.plan_registry.find_local_monthly_price(
        business.plan_key, business.currency_code
    )
    if local is not None:
        return local

    plan: PlanDefinition = prices.plan_registry.get(business.plan_key)
    return plan.monthly_price


def plan_return(
    monthly_price: Money | None,
    currency_code: CurrencyCode,
    date_from: date,
    date_to: date,
    estimated_revenue: EstimatedRevenueMinor | None,
) -> PlanReturn:
    """
    The plan's cost for the days from `date_from` to `date_to` and how many
    times the estimate covers it (one decimal); nothing when the plan is
    priced in another currency or is free, no multiple without an estimate.
    """

    if (
        monthly_price is None
        or monthly_price.currency_code != currency_code
        or int(monthly_price.amount_minor) <= 0
    ):
        return NO_RETURN

    cost: PlanCostMinor = plan_cost(monthly_price, date_from, date_to)
    if estimated_revenue is None or int(cost) == 0:
        return PlanReturn(plan_cost_minor=cost)

    multiple: Decimal = (Decimal(int(estimated_revenue)) / int(cost)).quantize(
        MULTIPLE_STEP, rounding=ROUND_HALF_UP
    )
    return PlanReturn(
        plan_cost_minor=cost, return_multiple=ValueReturnMultiple(float(multiple))
    )


def plan_cost(monthly_price: Money, date_from: date, date_to: date) -> PlanCostMinor:
    """The whole price for a calendar month, else its share of the days."""

    days: int = (date_to - date_from).days + 1
    month_days: int = calendar.monthrange(date_from.year, date_from.month)[1]
    if date_from.day == 1 and days == month_days:
        return PlanCostMinor(int(monthly_price.amount_minor))

    share: Decimal = (
        Decimal(int(monthly_price.amount_minor)) * days / AVERAGE_MONTH_DAYS
    )
    return PlanCostMinor(round_half_up(share))


def round_half_up(amount: Decimal) -> int:
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))
