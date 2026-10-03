import logging

from app.contracts.notifications import StaffDeliveryRecorderContract
from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
    StaffDeliveryStateRepoContract,
)
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.domain.outbound_messages import (
    OutboundMessageDocument,
    PushRecipient,
)
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument
from app.utilities.notifications.staff_delivery_keys import staff_delivery_state_id

logger: logging.Logger = logging.getLogger(__name__)


class StaffDeliveryRecorderFacilitator(StaffDeliveryRecorderContract):
    """
    Keeps how notifications to each staff contact go (the latest one's
    state and error, when one last arrived) and, for devices, when one last
    arrived or why it failed, so Settings shows whether notifications
    reach people. An older outcome never overwrites a newer one. Never
    raises: the record must not break a delivery.
    """

    def __init__(
        self,
        staff_delivery_state_repo: StaffDeliveryStateRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
    ) -> None:
        self._staff_delivery_state_repo: StaffDeliveryStateRepoContract = (
            staff_delivery_state_repo
        )
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )

    def record(self, message: OutboundMessageDocument) -> None:
        try:
            if message.staff_contact is not None:
                self._record_contact(message)
            elif message.push is not None:
                self._record_device(message, message.push)
        except Exception:
            logger.exception("The delivery state of %s was not recorded.", message.id)

    def _record_contact(self, message: OutboundMessageDocument) -> None:
        is_delivered: bool = message.status is OutboundMessageStatus.DELIVERED
        state_id = staff_delivery_state_id(message.business_id, message.recipient_key)

        def change(
            stored: StaffDeliveryStateDocument | None,
        ) -> StaffDeliveryStateDocument | None:
            if stored is not None and stored.attempted_at > message.updated_at:
                return None

            return StaffDeliveryStateDocument(
                id=state_id,
                business_id=message.business_id,
                status=message.status,
                last_error=None if is_delivered else message.last_error,
                attempted_at=message.updated_at,
                delivered_at=(
                    message.delivered_at
                    if is_delivered
                    else (None if stored is None else stored.delivered_at)
                ),
                created_at=message.created_at if stored is None else stored.created_at,
                updated_at=message.updated_at,
            )

        self._staff_delivery_state_repo.record(message.business_id, state_id, change)

    def _record_device(
        self,
        message: OutboundMessageDocument,
        recipient: PushRecipient,
    ) -> None:
        if message.status is OutboundMessageStatus.PENDING:
            return

        def change(
            subscription: PushSubscriptionDocument,
        ) -> PushSubscriptionDocument | None:
            if message.status is OutboundMessageStatus.DELIVERED:
                subscription.delivered_at = message.delivered_at
                subscription.last_error = None
            else:
                subscription.last_error = message.last_error

            subscription.updated_at = message.updated_at
            return subscription

        self._push_subscription_repo.update(
            message.business_id, recipient.subscription_id, change
        )
