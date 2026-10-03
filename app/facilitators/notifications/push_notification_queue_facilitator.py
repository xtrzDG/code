import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.notification_clients import WebPushClientContract
from app.contracts.notifications import (
    PushNotificationQueueContract,
    StaffDeliveryRecorderContract,
)
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.facilitators.notifications.staff_outbox_messages import (
    RATE_LIMITED_TEXT,
    queue_outbox_message,
)
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.notifications import WebPushUrgency
from app.schemas.domain.outbound_messages import (
    OutboundMessageDocument,
    PushRecipient,
)
from app.schemas.dto.notifications.staff_alerts import PushNotification
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.deliveries.delivery_keys import derive_outbound_message_id
from app.utilities.notifications.staff_delivery_keys import (
    HOURLY_DEVICE_LIMIT,
    RATE_WINDOW_SECONDS,
    push_idempotency_key,
    push_recipient_key,
    rate_limit_key,
)

logger: logging.Logger = logging.getLogger(__name__)


class PushNotificationQueueFacilitator(PushNotificationQueueContract):
    """
    Queues notifications for cabinet users' devices (Web Push) in the
    outbox, like a staff contact's: held through quiet hours, at most 30
    per device and hour, once per handoff and device. Nothing is queued
    while push is not configured (WEB_PUSH_VAPID_*). Never raises.
    """

    def __init__(
        self,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        web_push_client: WebPushClientContract | None,
        rate_limits: RequestRateLimitRegistryContract,
        delivery_recorder: StaffDeliveryRecorderContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._web_push_client: WebPushClientContract | None = web_push_client
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._delivery_recorder: StaffDeliveryRecorderContract = delivery_recorder
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def queue(self, notification: PushNotification) -> bool:
        if self._web_push_client is None:
            return False

        try:
            return self._queue(notification)
        except Exception:
            logger.exception("A device notification could not be queued.")
            return False

    def _queue(self, notification: PushNotification) -> bool:
        now: Microseconds = self._wall_clock.now_unix()
        idempotency_key: OutboundIdempotencyKey = push_idempotency_key(
            notification.subscription_id, notification.handoff_id
        )
        message_id = derive_outbound_message_id(
            notification.business_id, idempotency_key
        )
        stored: OutboundMessageDocument | None = self._outbound_message_repo.get(
            notification.business_id, message_id
        )
        if stored is not None:
            return stored.status is not OutboundMessageStatus.DEAD

        recipient_key: OutboundRecipientKey = push_recipient_key(
            notification.subscription_id
        )
        counter = RateLimitCounter(
            key=rate_limit_key(notification.business_id, recipient_key),
            limit=HOURLY_DEVICE_LIMIT,
        )
        refused_key: RateLimitKey | None = self._rate_limits.try_acquire_all(
            [counter], RATE_WINDOW_SECONDS, now
        )
        refusal: DeliveryErrorText | None = (
            None if refused_key is None else RATE_LIMITED_TEXT
        )
        detail = notification.brief.detail
        message = OutboundMessageDocument(
            id=message_id,
            business_id=notification.business_id,
            kind=OutboundMessageKind.STAFF_NOTIFICATION,
            idempotency_key=idempotency_key,
            recipient_key=recipient_key,
            push=PushRecipient(
                subscription_id=notification.subscription_id,
                user_id=notification.user_id,
                title=notification.brief.title,
                url=notification.link,
                tag=notification.tag,
                urgency=(
                    WebPushUrgency.HIGH
                    if notification.is_urgent
                    else WebPushUrgency.NORMAL
                ),
            ),
            text=MessageText("" if detail is None else str(detail)),
            handoff_id=notification.handoff_id,
            next_attempt_at=notification.deliver_after,
            created_at=now,
            updated_at=now,
        )
        return queue_outbox_message(
            message,
            refusal,
            self._outbound_message_repo,
            self._job_queue,
            self._delivery_recorder,
        )
