"""
A Flitt callback that pays or refunds (approved, reversed) takes effect
only when Flitt's status API (`/api/status/order_id`) says the same about
the order: the same status and, when both name one, the same amount. A
callback signed with a leaked key, or an old one delivered after the order
moved on, never marks an invoice paid or refunded on its own; it is
refused with a conflict, so the queued job that applies it tries again
(API-03) and the daily reconciliation compares what is left. Other
statuses (created, processing, declined, expired) change nothing that a
forged copy could profit from and are applied as verified.
"""

import logging

from app.adapters.payments.payment_fields import read_money
from app.adapters.payments.payment_status_reader_adapter import read_known_status
from app.clients.flitt.flitt_client import FlittClient
from app.schemas.constants.payments import PaymentStatus
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import PaymentNotification
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.payment_errors import PaymentProviderRefusedError

logger: logging.Logger = logging.getLogger(__name__)

CONFIRMED_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.APPROVED, PaymentStatus.REVERSED}
)


def confirm_flitt_notification(
    flitt_client: FlittClient, payment: PaymentNotification
) -> None:
    """
    Raises:
        ConflictError: Flitt reports another status or amount, or does not
            know the order.
        ExternalServiceError: Flitt could not be asked.
    """

    if payment.status not in CONFIRMED_STATUSES:
        return

    try:
        answer: dict[str, object] = flitt_client.read_order_status(
            str(payment.order_reference)
        )
    except PaymentProviderRefusedError as error:
        logger.warning(
            "Flitt does not confirm order %s of a %s notification.",
            payment.order_reference,
            payment.status.value,
        )
        raise ConflictError(
            "The payment provider does not confirm the order of this notification."
        ) from error

    reported: PaymentStatus | None = read_known_status(answer.get("order_status"))
    reported_amount: Money | None = read_money(
        answer.get("amount"), answer.get("currency")
    )
    if reported is not payment.status or (
        reported_amount is not None
        and payment.amount is not None
        and reported_amount != payment.amount
    ):
        logger.warning(
            "Flitt reports order %s as %s, not %s: the notification is not applied.",
            payment.order_reference,
            "unknown" if reported is None else reported.value,
            payment.status.value,
        )
        raise ConflictError(
            "The payment provider reports another state for this order; "
            "the notification is not applied."
        )
