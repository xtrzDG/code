"""
Identities of staff notifications: the delivery state of a contact, the
outbox keys of a device, and the per-recipient rate-limit keys.
"""

import hashlib
from uuid import UUID, uuid4, uuid5

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.notifications.prefixed_id import (
    PushSubscriptionId,
    StaffDeliveryStateId,
)
from app.schemas.typings.users.prefixed_id import UserId

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them).
STAFF_DELIVERY_NAMESPACE: UUID = UUID("9b1e4c2a-58d3-4f0e-a7c6-2d8f1b3e5a90")
PUSH_SUBSCRIPTION_NAMESPACE: UUID = UUID("d24a7f61-0c3e-4b9a-8e15-6f2b9c4d7a38")
RATE_KEY_DIGEST_LENGTH: int = 32
# Notifications one recipient may get per hour; more are not sent (a flood
# of handoffs is someone abusing the chat, and SMS cost money). Devices
# count as their own recipients.
HOURLY_LIMITS: dict[ManagerContactChannel, int] = {
    ManagerContactChannel.SMS: 10,
    ManagerContactChannel.WHATSAPP: 20,
    ManagerContactChannel.TELEGRAM: 30,
    ManagerContactChannel.EMAIL: 30,
}
HOURLY_DEVICE_LIMIT: int = 30
RATE_WINDOW_SECONDS: int = 60 * 60


def staff_delivery_state_id(
    business_id: BusinessId,
    recipient_key: OutboundRecipientKey,
) -> StaffDeliveryStateId:
    """The delivery state of one staff contact (from its recipient key)."""

    return StaffDeliveryStateId(
        uuid5(STAFF_DELIVERY_NAMESPACE, f"{business_id}|{recipient_key}")
    )


def push_subscription_id(
    business_id: BusinessId,
    user_id: UserId,
    endpoint: str,
) -> PushSubscriptionId:
    """The same browser subscribing again keeps its subscription."""

    return PushSubscriptionId(
        uuid5(PUSH_SUBSCRIPTION_NAMESPACE, f"{business_id}|{user_id}|{endpoint}")
    )


def push_recipient_key(subscription_id: PushSubscriptionId) -> OutboundRecipientKey:
    return OutboundRecipientKey(f"push:{subscription_id}")


def push_idempotency_key(
    subscription_id: PushSubscriptionId,
    handoff_id: HandoffId | None,
) -> OutboundIdempotencyKey:
    """A handoff reaches each device once; other alerts are new each time."""

    subject: str = str(uuid4()) if handoff_id is None else f"handoff:{handoff_id}"
    return OutboundIdempotencyKey(f"push:{subject}:{subscription_id}")


def rate_limit_key(
    business_id: BusinessId,
    recipient_key: OutboundRecipientKey,
) -> str:
    """The rate-limit counter of one recipient (a digest: no address in it)."""

    digest: str = hashlib.sha256(f"{business_id}|{recipient_key}".encode()).hexdigest()
    return f"staff_notify:{digest[:RATE_KEY_DIGEST_LENGTH]}"
