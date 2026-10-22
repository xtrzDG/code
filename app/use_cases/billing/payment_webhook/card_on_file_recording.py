"""
The card on file: what a provider says about the card it saved for the
automatic charges of a payment order (with the first payment, through a
card setup, or replaced through the provider's own page).
"""

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.payments import PaymentOrderPurpose, PaymentStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentMethodNotice, PaymentNotification
from app.schemas.typings.billing.strings import PaymentNotificationKey
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.billing.payment_webhook.checkout_payment_settlement import (
    replace_charge_schedule,
)
from app.use_cases.billing.payment_webhook.payment_order_rules import (
    build_order_reference,
)

CARD_NOTICE_SUFFIX: str = "card"


def build_card_notice_key(notice: PaymentMethodNotice) -> PaymentNotificationKey:
    """One key per provider event that saved a card: each is applied once."""

    return PaymentNotificationKey(f"{notice.event_reference}:{CARD_NOTICE_SUFFIX}")


def record_card_references(
    notice: PaymentMethodNotice,
    payment_order: PaymentOrderDocument,
    secret_cipher: SecretCipherAdapterContract,
) -> None:
    """
    The provider's references of what the order started (Stripe's
    subscription and customer) and the card's token, sealed with the
    platform's key ring (Flitt's rectoken, for the retries).
    """

    if notice.schedule_reference is not None:
        payment_order.schedule_reference = notice.schedule_reference

    if notice.customer_reference is not None:
        payment_order.customer_reference = notice.customer_reference

    if notice.card_token is not None:
        payment_order.sealed_card_token = secret_cipher.encrypt(
            ChannelSecret(str(notice.card_token))
        )


def is_pending_card_setup(payment_order: PaymentOrderDocument) -> bool:
    return (
        payment_order.purpose is PaymentOrderPurpose.CARD_SETUP
        and not payment_order.is_initial_payment_settled
    )


def settle_card_setup(
    payment_gateway: PaymentGatewayAdapterContract,
    payment_order: PaymentOrderDocument,
    subscription: SubscriptionDocument,
) -> None:
    """
    A card setup saved its card: its automatic charges become the
    subscription's (those of an earlier checkout stop). Nothing is paid,
    so no invoice changes; a cancelled subscription stays cancelled.
    """

    replace_charge_schedule(payment_gateway, payment_order, subscription)
    payment_order.is_initial_payment_settled = True
    payment_order.status = PaymentStatus.APPROVED


def is_card_setup_verification(
    notification: PaymentNotification, payment_order: PaymentOrderDocument
) -> bool:
    """
    The card setup's own verification (Flitt charges nothing for it), not
    an automatic charge of its schedule nor a retry.
    """

    return (
        payment_order.purpose is PaymentOrderPurpose.CARD_SETUP
        and notification.parent_order_reference is None
        and not notification.is_retry
        and str(notification.order_reference) == str(payment_order.id)
    )


def keep_current_card(
    subscription: SubscriptionDocument,
    payment_order: PaymentOrderDocument,
    summary: PaymentMethodSummary,
) -> bool:
    """
    The card becomes the subscription's card on file (True) when the
    order's charges are the ones that run, unless a newer card was saved
    already (an older event that arrives late).
    """

    if subscription.provider_reference != build_order_reference(payment_order):
        return False

    current: PaymentMethodSummary | None = subscription.payment_method_summary
    if current is not None and int(current.saved_at) > int(summary.saved_at):
        return False

    subscription.payment_method_summary = summary
    return True
