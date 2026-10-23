"""
Which declined automatic charge the retries are for, and how far along
they are: the latest FAILED service period charged by the running
schedule of a past-due subscription.
"""

from typed_time_provider import Microseconds

from app.contracts.billing import PaymentOrderRepoContract
from app.contracts.payment_methods import PaymentRetryRepoContract
from app.contracts.registries import PlanRegistryContract
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.payments import PaymentRetryOutcome
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_methods import PaymentRetryView
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    build_order_reference,
)
from app.utilities.billing.dunning_schedule import (
    find_grace_start,
    find_next_retry_at,
)


def find_dunning_invoice(
    subscription: SubscriptionDocument, invoices: list[InvoiceDocument]
) -> InvoiceDocument | None:
    """
    The declined automatic charge of a past-due subscription whose charges
    still run (an invoice the provider charged, now FAILED); None when
    there is nothing to retry.
    """

    if (
        subscription.status is not SubscriptionStatus.PAST_DUE
        or subscription.grace_until is None
        or subscription.provider_reference is None
    ):
        return None

    declined: list[InvoiceDocument] = [
        invoice
        for invoice in invoices
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status is InvoiceStatus.FAILED
        and invoice.provider_reference is not None
    ]
    return max(declined, key=lambda invoice: int(invoice.created_at), default=None)


# A retry the provider took (or is still taking): its notice settles the
# invoice, so no further retry charges the card for it meanwhile.
SETTLING_RETRY_OUTCOMES: frozenset[PaymentRetryOutcome] = frozenset(
    {PaymentRetryOutcome.APPROVED, PaymentRetryOutcome.PROCESSING}
)


def has_settling_retry(
    retry_repo: PaymentRetryRepoContract,
    business_id: BusinessId,
    invoice_id: InvoiceId,
) -> bool:
    """
    An earlier retry of the invoice was approved or is being processed and
    its notice has not said otherwise yet: charging the card again could
    take the money twice.
    """

    return any(
        attempt.outcome in SETTLING_RETRY_OUTCOMES
        for attempt in retry_repo.list_for_invoice(business_id, invoice_id)
    )


def find_grace_start_of(
    plan_registry: PlanRegistryContract,
    subscription: SubscriptionDocument,
    business: BusinessDocument,
) -> Microseconds | None:
    if subscription.grace_until is None:
        return None

    return find_grace_start(
        subscription.grace_until,
        plan_registry.get(subscription.plan_key).grace_period_days,
        business.timezone,
    )


def find_schedule_order(
    payment_order_repo: PaymentOrderRepoContract,
    subscription: SubscriptionDocument,
) -> PaymentOrderDocument | None:
    """The payment order whose automatic charges the subscription runs."""

    if subscription.provider_reference is None:
        return None

    return next(
        (
            order
            for order in payment_order_repo.list_by_business(subscription.business_id)
            if order.subscription_id == subscription.id
            and build_order_reference(order) == subscription.provider_reference
        ),
        None,
    )


def build_retry_view(
    retry_repo: PaymentRetryRepoContract,
    invoice: InvoiceDocument,
    subscription: SubscriptionDocument,
    business: BusinessDocument,
    grace_start: Microseconds,
) -> PaymentRetryView:
    attempts: list[PaymentRetryAttemptDocument] = retry_repo.list_for_invoice(
        business.id, invoice.id
    )
    last: PaymentRetryAttemptDocument | None = attempts[-1] if attempts else None
    last_attempt: PaymentRetryAttempt | None = None if last is None else last.attempt
    next_retry_at: Microseconds | None = find_next_retry_at(
        grace_start, last_attempt, business.timezone
    )
    if (
        next_retry_at is not None
        and subscription.grace_until is not None
        and next_retry_at >= subscription.grace_until
    ):
        next_retry_at = None

    return PaymentRetryView(
        last_attempt=last_attempt,
        last_outcome=None if last is None else last.outcome,
        next_retry_at=next_retry_at,
        grace_until=subscription.grace_until,
    )
