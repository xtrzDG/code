"""What one verified payment notification hands the status rules."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import PaymentNotification


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
