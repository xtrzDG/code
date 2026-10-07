"""
What the cancel dialog can offer a business instead of cancelling: a
seasonal pause, the next cheaper plan, or a one-time credit from the
ledger. Each reason takes the first offer of its list the business can
have now (`SubscriptionLifecyclePolicy.offers`).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.registries import PlanRegistryContract
from app.schemas.constants.billing import PlanKey, SubscriptionStatus
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.dto.subscription_lifecycle import PauseAvailability
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.use_cases.shared.subscription_pricing import price_subscription
from app.utilities.billing.pause_pricing import (
    monthly_price_minor,
    pause_month_price_minor,
    share_of_minor,
)

# A cheaper plan or a credit keeps a business that still pays or tries to.
KEEPABLE_STATUSES: frozenset[SubscriptionStatus] = frozenset(
    {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
        SubscriptionStatus.PAST_DUE,
    }
)


@dataclass(frozen=True)
class OfferInputs:
    """What the business can have now: each None when it cannot."""

    pause: PauseAvailability
    pause_price: Money | None
    cheaper_plan: PlanDefinition | None
    cheaper_price: Money | None
    save_credit: Money | None


def gather_offer_inputs(
    subscription: SubscriptionDocument | None,
    pause: PauseAvailability,
    credit_lines: Sequence[BillingCreditDocument],
    plan_registry: PlanRegistryContract,
    policy: SubscriptionLifecyclePolicy,
) -> OfferInputs:
    if subscription is None:
        return OfferInputs(pause, None, None, None, None)

    cheaper: tuple[PlanDefinition, Money] | None = find_cheaper_plan(
        plan_registry, subscription
    )
    return OfferInputs(
        pause=pause,
        pause_price=Money(
            amount_minor=MoneyAmountMinor(
                pause_month_price_minor(subscription, int(policy.pause_price_percent))
            ),
            currency_code=subscription.currency_code,
        ),
        cheaper_plan=None if cheaper is None else cheaper[0],
        cheaper_price=None if cheaper is None else cheaper[1],
        save_credit=save_credit_amount(subscription, credit_lines, policy),
    )


def offer_for(
    reason: CancellationReason,
    policy: SubscriptionLifecyclePolicy,
    inputs: OfferInputs,
) -> RetentionOfferKind | None:
    """The first offer of the reason's list the business can have now."""

    for kind in policy.offers.get(reason, []):
        if is_offer_open(kind, inputs):
            return kind

    return None


def is_offer_open(kind: RetentionOfferKind, inputs: OfferInputs) -> bool:
    match kind:
        case RetentionOfferKind.PAUSE:
            return inputs.pause.unavailable_reason is None
        case RetentionOfferKind.DOWNGRADE:
            return inputs.cheaper_plan is not None
        case RetentionOfferKind.CREDIT:
            return inputs.save_credit is not None


def find_cheaper_plan(
    plan_registry: PlanRegistryContract,
    subscription: SubscriptionDocument,
) -> tuple[PlanDefinition, Money] | None:
    """
    The dearest plan below the current price, same billing period and
    currency (the next step down); None for the cheapest plan or a
    subscription not being paid for.
    """

    if subscription.status not in KEEPABLE_STATUSES:
        return None

    candidates: list[tuple[PlanDefinition, Money]] = []
    for plan in plan_registry.list_all():
        if plan.key is subscription.plan_key:
            continue

        price: Money | None = _price(plan_registry, plan.key, subscription)
        if price is not None and int(price.amount_minor) < int(
            subscription.price_minor
        ):
            candidates.append((plan, price))

    if candidates == []:
        return None

    return max(candidates, key=lambda candidate: int(candidate[1].amount_minor))


def save_credit_amount(
    subscription: SubscriptionDocument,
    credit_lines: Sequence[BillingCreditDocument],
    policy: SubscriptionLifecyclePolicy,
) -> Money | None:
    """
    The one-time credit (a share of a month of the plan, in the
    subscription currency); None once the business had it.
    """

    if subscription.status not in KEEPABLE_STATUSES or any(
        line.save_offer_for is not None for line in credit_lines
    ):
        return None

    amount: int = share_of_minor(
        monthly_price_minor(subscription), int(policy.save_credit_percent)
    )
    if amount <= 0:
        return None

    return Money(
        amount_minor=MoneyAmountMinor(amount),
        currency_code=subscription.currency_code,
    )


def _price(
    plan_registry: PlanRegistryContract,
    plan_key: PlanKey,
    subscription: SubscriptionDocument,
) -> Money | None:
    try:
        return price_subscription(
            plan_registry,
            plan_key,
            subscription.billing_period,
            subscription.currency_code,
        )
    except NotFoundError, ValidationFailedError:
        return None
