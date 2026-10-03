"""What a payment notification may do to its payment order."""

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.payments import PaymentStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import PaymentNotification
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.strings import (
    PaymentNotificationKey,
    PaymentProviderReference,
)

FINAL_ORDER_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.APPROVED, PaymentStatus.REVERSED}
)


def build_notification_key(notification: PaymentNotification) -> PaymentNotificationKey:
    """One key per (payment, status) pair: each pair is applied once."""

    return PaymentNotificationKey(
        f"{notification.payment_reference or notification.order_reference}"
        f":{notification.status.value}"
    )


def require_expected_amount(
    notification: PaymentNotification,
    payment_order: PaymentOrderDocument,
) -> None:
    """
    An approval is for the checkout's amount, or for the recurring amount
    once the first payment is settled.

    Raises:
        ValidationFailedError: another amount or currency.
    """

    expected_amount: int = int(
        payment_order.recurring_amount_minor
        if payment_order.is_initial_payment_settled
        else payment_order.amount_minor
    )
    amount: Money | None = notification.amount
    if (
        amount is None
        or amount.currency_code != payment_order.currency_code
        or int(amount.amount_minor) != expected_amount
    ):
        raise ValidationFailedError(
            "The approved amount does not match the payment order."
        )


def is_stray_charge(
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
) -> bool:
    """
    An automatic charge of a schedule the subscription no longer uses:
    replaced by a later checkout, stopped by a plan change, or of a
    cancelled subscription.
    """

    return payment_order.is_initial_payment_settled and (
        subscription.status is SubscriptionStatus.CANCELLED
        or subscription.provider_reference != build_order_reference(payment_order)
    )


def build_order_reference(
    payment_order: PaymentOrderDocument,
) -> PaymentProviderReference:
    """Provider reference of the automatic charges a checkout started."""

    return PaymentProviderReference(str(payment_order.id))
