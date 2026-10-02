"""How a payment moves a subscription between trial, active and past due."""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.use_cases.billing.billing_records import (
    find_covering_paid_invoice,
    list_subscription_invoices,
)


def resume_cancelled_subscription(
    subscription: SubscriptionDocument,
    now: Microseconds,
) -> None:
    """
    A checkout paid after cancelling resumes the subscription: the trial
    while it still runs, otherwise the paid period (see
    `activate_paid_period`).
    """

    if subscription.status is not SubscriptionStatus.CANCELLED:
        return

    if subscription.trial_ends_at is not None and now < subscription.trial_ends_at:
        subscription.status = SubscriptionStatus.TRIALING


def activate_paid_period(
    invoice_repo: InvoiceRepoContract,
    subscription: SubscriptionDocument,
    now: Microseconds,
) -> None:
    """
    The paid period that has started becomes current and ends any grace; a
    trial paid ahead stays in trial until it ends.
    """

    is_trial_running: bool = (
        subscription.status is SubscriptionStatus.TRIALING
        and subscription.trial_ends_at is not None
        and now < subscription.trial_ends_at
    )
    if is_trial_running:
        return

    covering: InvoiceDocument | None = find_covering_paid_invoice(
        list_subscription_invoices(invoice_repo, subscription),
        now,
    )
    if covering is None:
        return

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.period_start = covering.period_start
    subscription.period_end = covering.period_end
    subscription.grace_until = None
