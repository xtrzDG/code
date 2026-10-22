"""The first payment of a checkout: its bills and its charge schedule."""

from typed_time_provider import Microseconds

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.billing_profiles import PaymentCardSnapshot
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.use_cases.billing.payment_webhook.payment_invoice_settlement import (
    settle_order_invoices,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    build_order_reference,
)
from app.use_cases.shared.recurring_charges import stop_recurring_charges
from app.use_cases.shared.subscription_payment_transitions import (
    resume_cancelled_subscription,
)


def settle_checkout_payment(
    payment_gateway: PaymentGatewayAdapterContract,
    invoice_repo: InvoiceRepoContract,
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
    payment_reference: PaymentProviderReference | None,
    now: Microseconds,
    *,
    card: PaymentCardSnapshot | None = None,
) -> PaymentWebhookOutcome:
    """
    The checkout's invoices become PAID and its automatic charges replace
    those of an earlier checkout, so only one schedule ever runs; a
    cancelled subscription is resumed. Money that settles no bill is
    REFUND_DUE.
    """

    replace_charge_schedule(payment_gateway, payment_order, subscription)
    outcome: PaymentWebhookOutcome = PaymentWebhookOutcome.APPLIED
    settled_count: int = settle_order_invoices(
        invoice_repo,
        payment_order,
        subscription,
        InvoiceStatus.PAID,
        payment_reference,
        now,
        card=card,
    )
    # Money that books nothing (a bill paid twice, a second setup
    # fee, a month overlapping a paid one) is owed back.
    if settled_count < len(payment_order.invoice_ids):
        payment_order.is_refund_due = True
        outcome = PaymentWebhookOutcome.REFUND_DUE

    payment_order.is_initial_payment_settled = True
    resume_cancelled_subscription(subscription, now)
    return outcome


def replace_charge_schedule(
    payment_gateway: PaymentGatewayAdapterContract,
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
) -> None:
    """
    The order's automatic charges become the subscription's, at its
    provider; those of an earlier checkout or card setup stop, so only one
    schedule ever runs (the earlier card is forgotten with them).
    """

    order_reference: PaymentProviderReference = build_order_reference(payment_order)
    if subscription.provider_reference != order_reference:
        stop_recurring_charges(payment_gateway, subscription)

    subscription.provider_reference = order_reference
    subscription.payment_provider = payment_order.provider


def decline_checkout_payment(
    invoice_repo: InvoiceRepoContract,
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
    payment_reference: PaymentProviderReference | None,
    now: Microseconds,
) -> Money:
    """The checkout's open invoices become FAILED; returns the amount refused."""

    settle_order_invoices(
        invoice_repo,
        payment_order,
        subscription,
        InvoiceStatus.FAILED,
        payment_reference,
        now,
    )
    return Money(
        amount_minor=payment_order.amount_minor,
        currency_code=payment_order.currency_code,
    )
