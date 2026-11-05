"""
What the assistant returned against its price: the money estimate of a
period divided by what the business's plan costs for the same days
("≈ 3.7× the plan price"). Only in the business currency: a plan paid in
another currency is never converted, so it gives no multiple. A business
in its free trial pays nothing for the period, so it gets no multiple
either, only what the plan will cost a month once the trial ends.
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from typed_time_provider import Microseconds

from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.schemas.constants.billing import BillingPeriod, SubscriptionStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.booleans import IsTrialPeriod
from app.schemas.typings.value.constrained_floats import ValueReturnMultiple
from app.schemas.typings.value.constrained_integers import (
    EstimatedRevenueMinor,
    MonthlyPlanPriceMinor,
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
class PlanTerms:
    """
    What the business pays a month (None: nothing known), and whether its
    subscription is in the free trial (until `trial_ends_at`).
    """

    monthly_price: Money | None
    is_trial: IsTrialPeriod = False
    trial_ends_at: Microseconds | None = None


@dataclass(frozen=True)
class PlanReturn:
    """
    The plan's cost for a period and the multiple the money made of it; in
    the free trial neither, but the monthly price that follows it.
    """

    plan_cost_minor: PlanCostMinor | None = None
    return_multiple: ValueReturnMultiple | None = None
    is_trial: IsTrialPeriod = False
    trial_ends_at: Microseconds | None = None
    price_after_trial: MonthlyPlanPriceMinor | None = None


NO_RETURN: PlanReturn = PlanReturn()


def read_plan_terms(prices: PlanPrices, business: BusinessDocument) -> PlanTerms:
    """
    What the business pays a month: its subscription's price (an annual one
    spread over twelve months, a trial one being what follows the trial),
    else its plan's price in its own currency (a business still setting up).
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
        is_trial: bool = subscription.status is SubscriptionStatus.TRIALING
        return PlanTerms(
            monthly_price=Money.model_validate(
                {
                    "amount_minor": round_half_up(
                        Decimal(int(subscription.price_minor)) / months
                    ),
                    "currency_code": subscription.currency_code,
                }
            ),
            is_trial=is_trial,
            trial_ends_at=subscription.trial_ends_at if is_trial else None,
        )

    local: Money | None = prices.plan_registry.find_local_monthly_price(
        business.plan_key, business.currency_code
    )
    if local is not None:
        return PlanTerms(monthly_price=local)

    plan: PlanDefinition = prices.plan_registry.get(business.plan_key)
    return PlanTerms(monthly_price=plan.monthly_price)


def plan_return(
    terms: PlanTerms,
    currency_code: CurrencyCode,
    date_from: date,
    date_to: date,
    estimated_revenue: EstimatedRevenueMinor | None,
) -> PlanReturn:
    """
    The plan's cost for the days from `date_from` to `date_to` and how many
    times the estimate covers it (one decimal): nothing when the plan is
    priced in another currency or is free; in the free trial no cost and
    no multiple, only the monthly price after it; no multiple without an
    estimate, for an estimate of nothing, or one rounding to 0.0.
    """

    price: Money | None = terms.monthly_price
    is_priced: bool = (
        price is not None
        and price.currency_code == currency_code
        and int(price.amount_minor) > 0
    )
    if terms.is_trial:
        return PlanReturn(
            is_trial=True,
            trial_ends_at=terms.trial_ends_at,
            price_after_trial=(
                MonthlyPlanPriceMinor(int(price.amount_minor))
                if price is not None and is_priced
                else None
            ),
        )

    if price is None or not is_priced:
        return NO_RETURN

    cost: PlanCostMinor = plan_cost(price, date_from, date_to)
    if estimated_revenue is None or int(estimated_revenue) <= 0 or int(cost) == 0:
        return PlanReturn(plan_cost_minor=cost)

    multiple: Decimal = (Decimal(int(estimated_revenue)) / int(cost)).quantize(
        MULTIPLE_STEP, rounding=ROUND_HALF_UP
    )
    if multiple <= 0:
        return PlanReturn(plan_cost_minor=cost)

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
