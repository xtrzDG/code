"""
What one verified payment notification hands the status rules, and the
payload of the job that applies it.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentNotification
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.channels.strings import EncryptedChannelSecret


class PaymentStatusChange(ImmutableDTO):
    """
    A payment's new status with the order, subscription and business it
    changes; the rules change the documents in place and the caller saves
    the order.
    """

    notification: PaymentNotification
    payment_order: PaymentOrderDocument
    subscription: SubscriptionDocument
    business: BusinessDocument


class QueuedPaymentNotification(ImmutableDTO):
    """
    The payload of the job `apply_payment_notification`: the payment order
    a verified notification is about, and the verified event itself as
    JSON sealed with the platform's key ring (it may carry the token of a
    saved card, and job payloads are stored and shown in plain text).
    """

    payment_order_id: PaymentOrderId
    sealed_event: EncryptedChannelSecret
