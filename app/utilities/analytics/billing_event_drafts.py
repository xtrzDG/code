"""
The product events of the billing steps: each carries what the
subscription brings a month after the step, the base of the MRR movements.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.constants.payments import PaymentStatus, PaymentWebhookOutcome
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.product_events import ProductEventProperties
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.typings.analytics.constrained_integers import (
    MonthlyRecurringAmountMinor,
)
from app.schemas.typings.users.prefixed_id import UserId

MONTHS_PER_YEAR: int = 12


def billing_event(
    name: ProductEventName,
    subscription: SubscriptionDocument,
    user_id: UserId | None = None,
    previous_plan_key: PlanKey | None = None,
    occurred_at: Microseconds | None = None,
) -> ProductEventDraft:
    """
    A billing step with what the subscription brings a month after it (the
    monthly price, or the annual one spread over twelve months).
    """

    return ProductEventDraft(
        name=name,
        user_id=user_id,
        business_id=subscription.business_id,
        properties=ProductEventProperties(
            plan_key=subscription.plan_key,
            previous_plan_key=previous_plan_key,
            billing_period=subscription.billing_period,
            monthly_amount=monthly_recurring_amount(subscription),
            currency_code=subscription.currency_code,
            trial_ends_at=subscription.trial_ends_at,
        ),
        occurred_at=occurred_at,
    )


def monthly_recurring_amount(
    subscription: SubscriptionDocument,
) -> MonthlyRecurringAmountMinor:
    """The subscription's price per month, rounded to whole minor units."""

    price: int = int(subscription.price_minor)
    if subscription.billing_period is BillingPeriod.ANNUAL:
        return MonthlyRecurringAmountMinor(
            (price + MONTHS_PER_YEAR // 2) // MONTHS_PER_YEAR
        )

    return MonthlyRecurringAmountMinor(price)


def subscription_started_events(
    previous_status: SubscriptionStatus, subscription: SubscriptionDocument
) -> tuple[ProductEventDraft, ...]:
    """
    SUBSCRIBED when a payment made the subscription ACTIVE (a first paid
    period, a resumed or recovered one); none for a renewal of an active one
    or a trial paid ahead (it turns paid when the trial ends).
    """

    if (
        previous_status is SubscriptionStatus.ACTIVE
        or subscription.status is not SubscriptionStatus.ACTIVE
    ):
        return ()

    return (billing_event(ProductEventName.SUBSCRIBED, subscription),)


def payment_events(
    payment_status: PaymentStatus,
    outcome: PaymentWebhookOutcome,
    previous_status: SubscriptionStatus,
    subscription: SubscriptionDocument,
) -> tuple[ProductEventDraft, ...]:
    """
    What a payment notification did: an approved payment that made the
    subscription ACTIVE subscribed it; a declined charge that was applied
    (not a stray schedule's) is a failed payment.
    """

    if payment_status is PaymentStatus.APPROVED:
        return subscription_started_events(previous_status, subscription)

    if (
        payment_status is PaymentStatus.DECLINED
        and outcome is PaymentWebhookOutcome.APPLIED
    ):
        return (billing_event(ProductEventName.PAYMENT_FAILED, subscription),)

    return ()
