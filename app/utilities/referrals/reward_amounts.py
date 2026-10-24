"""
The month of service an invitation's reward is worth: one month of the
plan a business pays, in the currency it pays (its subscription's), before
tax; a business without a subscription is quoted the plan's monthly price
in its own currency where the price book has one, else in the plan's.
"""

from collections.abc import Sequence

from app.contracts.registries import PlanRegistryContract
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money, PlanDefinition


def latest_subscription(
    subscriptions: Sequence[SubscriptionDocument],
) -> SubscriptionDocument | None:
    """The most recently created subscription of a business, if any."""

    return max(
        subscriptions,
        key=lambda subscription: (int(subscription.created_at), subscription.id),
        default=None,
    )


def month_of_service(
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    subscription: SubscriptionDocument | None,
) -> Money:
    """One month of the business's plan before tax, in the currency it pays."""

    if subscription is not None:
        price: Money | None = plan_registry.find_local_monthly_price(
            subscription.plan_key, subscription.currency_code
        )
        if price is not None:
            return price

    local: Money | None = plan_registry.find_local_monthly_price(
        business.plan_key, business.currency_code
    )
    if local is not None:
        return local

    plan: PlanDefinition = plan_registry.get(business.plan_key)
    return plan.monthly_price
