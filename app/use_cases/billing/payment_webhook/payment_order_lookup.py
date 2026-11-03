"""Find the payment order a provider notification is about."""

from app.contracts.billing import PaymentOrderRepoContract
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentNotification, VerifiedPaymentEvent
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import PaymentProviderReference


def find_event_order(
    payment_order_repo: PaymentOrderRepoContract,
    event: VerifiedPaymentEvent,
) -> PaymentOrderDocument | None:
    """
    The payment order of a verified event: its payment's order, else its
    saved card's; None for an event that names neither (nothing to act on).

    Raises:
        NotFoundError: the event names an order the platform does not know.
    """

    if event.payment is not None:
        return find_payment_order(payment_order_repo, event.payment)

    if event.payment_method is not None:
        return find_payment_order_by_reference(
            payment_order_repo, event.payment_method.order_reference
        )

    return None


def find_payment_order(
    payment_order_repo: PaymentOrderRepoContract,
    notification: PaymentNotification,
) -> PaymentOrderDocument:
    """
    By the order id we sent, else the parent order of an automatic charge,
    else the echoed merchant data.

    Raises:
        NotFoundError: none of them names a payment order.
    """

    for reference in (
        notification.order_reference,
        notification.parent_order_reference,
        notification.merchant_reference,
    ):
        payment_order_id: PaymentOrderId | None = parse_payment_order_id(reference)
        if payment_order_id is None:
            continue

        payment_order: PaymentOrderDocument | None = payment_order_repo.get(
            payment_order_id
        )
        if payment_order is not None:
            return payment_order

    raise NotFoundError("Payment order was not found.")


def find_payment_order_by_reference(
    payment_order_repo: PaymentOrderRepoContract,
    reference: PaymentProviderReference,
) -> PaymentOrderDocument:
    """
    Raises:
        NotFoundError: the reference names no payment order.
    """

    payment_order_id: PaymentOrderId | None = parse_payment_order_id(reference)
    payment_order: PaymentOrderDocument | None = (
        None if payment_order_id is None else payment_order_repo.get(payment_order_id)
    )
    if payment_order is None:
        raise NotFoundError("Payment order was not found.")

    return payment_order


def parse_payment_order_id(
    reference: PaymentProviderReference | None,
) -> PaymentOrderId | None:
    """Our payment order id inside a provider reference, if it is one."""

    if reference is None:
        return None

    try:
        return PaymentOrderId(str(reference))
    except TypeError, ValueError:
        return None
