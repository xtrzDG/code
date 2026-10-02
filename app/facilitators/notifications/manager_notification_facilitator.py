import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.notifications import StaffDeliveryRecorderContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.facilitators.notifications.staff_outbox_messages import (
    RATE_LIMITED_TEXT,
    queue_outbox_message,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.utilities.deliveries.delivery_keys import (
    derive_outbound_message_id,
    staff_idempotency_key,
    staff_recipient_key,
)
from app.utilities.notifications.staff_delivery_keys import (
    HOURLY_LIMITS,
    RATE_WINDOW_SECONDS,
    rate_limit_key,
)
from app.utilities.notifications.staff_providers import (
    missing_staff_provider,
    staff_template,
)

logger: logging.Logger = logging.getLogger(__name__)


class ManagerNotificationFacilitator(ManagerNotificationFacilitatorContract):
    """
    Queues staff notifications (handoffs, bookings, leads, billing notices)
    in the outbox; the worker sends them with retries (`deliver_outbound`),
    so a provider outage delays a notification instead of losing it, and
    its delivery state is stored (and shown per contact in Settings).

    A notification is held until `deliver_after` (the contact's quiet
    hours). A contact whose channel has no provider (the platform bot, the
    WhatsApp template, SMTP or Twilio is not configured; e-mail and SMS are
    logged outside production), or that already got its hourly share of
    notifications (SMS 10, WhatsApp 20, others 30), is stored as DEAD with
    the reason and reported as not deliverable. A notification about a
    handoff is queued once per handoff and contact. Never raises: a
    notification must not break the action it reports.
    """

    def __init__(
        self,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        app_settings: AppSettings,
        rate_limits: RequestRateLimitRegistryContract,
        delivery_recorder: StaffDeliveryRecorderContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._app_settings: AppSettings = app_settings
        self._rate_limits: RequestRateLimitRegistryContract = rate_limits
        self._delivery_recorder: StaffDeliveryRecorderContract = delivery_recorder
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def notify(self, notification: StaffNotification) -> bool:
        try:
            return self._queue(notification)
        except Exception:
            logger.exception(
                "Staff notification through %s could not be queued.",
                notification.contact.channel.value,
            )
            return False

    def _queue(self, notification: StaffNotification) -> bool:
        now: Microseconds = self._wall_clock.now_unix()
        contact: ManagerContact = notification.contact
        idempotency_key: OutboundIdempotencyKey = staff_idempotency_key(
            contact, notification.handoff_id
        )
        message_id = derive_outbound_message_id(
            notification.business_id, idempotency_key
        )
        stored: OutboundMessageDocument | None = self._outbound_message_repo.get(
            notification.business_id, message_id
        )
        if stored is not None:
            # Queued before (a handoff step that ran again).
            return stored.status is not OutboundMessageStatus.DEAD

        recipient_key: OutboundRecipientKey = staff_recipient_key(contact)
        refusal: DeliveryErrorText | None = missing_staff_provider(
            self._app_settings, contact.channel
        ) or self._refusal_by_rate(notification, recipient_key, now)
        message = OutboundMessageDocument(
            id=message_id,
            business_id=notification.business_id,
            kind=OutboundMessageKind.STAFF_NOTIFICATION,
            idempotency_key=idempotency_key,
            recipient_key=recipient_key,
            staff_contact=contact,
            text=notification.text,
            template=staff_template(self._app_settings, contact),
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

    def _refusal_by_rate(
        self,
        notification: StaffNotification,
        recipient_key: OutboundRecipientKey,
        now: Microseconds,
    ) -> DeliveryErrorText | None:
        limit: int = HOURLY_LIMITS[notification.contact.channel]
        refused_key: str | None = self._rate_limits.try_acquire_all(
            [(rate_limit_key(notification.business_id, recipient_key), limit)],
            RATE_WINDOW_SECONDS,
            now,
        )
        return None if refused_key is None else RATE_LIMITED_TEXT
