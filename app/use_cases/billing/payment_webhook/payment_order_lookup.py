"""Find the payment order a provider notification is about."""

from app.contracts.billing import PaymentOrderRepoContract
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentNotification
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import PaymentProviderReference


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
