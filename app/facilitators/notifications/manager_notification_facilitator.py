import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import (
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import (
    derive_outbound_message_id,
    outbound_serial_key,
    staff_idempotency_key,
    staff_recipient_key,
)

logger: logging.Logger = logging.getLogger(__name__)


class ManagerNotificationFacilitator(ManagerNotificationFacilitatorContract):
    """
    Queues staff notifications (handoffs, bookings, leads, billing notices)
    in the outbox; the worker sends them with retries (`deliver_outbound`),
    so a provider outage delays a notification instead of losing it, and
    its delivery state is stored.

    A contact whose channel has no provider (the platform bot or the
    WhatsApp template is not configured; e-mail and SMS in production) is
    stored as DEAD with the reason and reported as not deliverable. A
    notification about a handoff is queued once per handoff and contact.
    Never raises: a notification must not break the action it reports.
    """

    def __init__(
        self,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._app_settings: AppSettings = app_settings
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
        missing_provider: DeliveryErrorText | None = self._missing_provider(contact)
        idempotency_key: OutboundIdempotencyKey = staff_idempotency_key(
            contact, notification.handoff_id
        )
        recipient_key: OutboundRecipientKey = staff_recipient_key(contact)
        message = OutboundMessageDocument(
            id=derive_outbound_message_id(notification.business_id, idempotency_key),
            business_id=notification.business_id,
            kind=OutboundMessageKind.STAFF_NOTIFICATION,
            idempotency_key=idempotency_key,
            recipient_key=recipient_key,
            staff_contact=contact,
            text=notification.text,
            template=self._template(contact),
            handoff_id=notification.handoff_id,
            status=(
                OutboundMessageStatus.PENDING
                if missing_provider is None
                else OutboundMessageStatus.DEAD
            ),
            last_error=missing_provider,
            created_at=now,
            updated_at=now,
        )
        if not self._outbound_message_repo.insert_if_new(message):
            stored: OutboundMessageDocument | None = self._outbound_message_repo.get(
                message.business_id, message.id
            )
            return (
                stored is not None and stored.status is not OutboundMessageStatus.DEAD
            )

        if missing_provider is not None:
            logger.warning(
                "Staff notification by %s cannot be delivered: %s",
                contact.channel.value,
                missing_provider,
            )
            return False

        self._job_queue.enqueue(
            DELIVER_OUTBOUND_JOB,
            encode_outbound_message_payload(message.id),
            message.business_id,
            lane=JobLane.OUTBOUND,
            serial_key=outbound_serial_key(message.business_id, recipient_key),
        )
        return True

    def _template(self, contact: ManagerContact) -> OutboundTemplate | None:
        template_name: WhatsAppTemplateName | None = (
            self._app_settings.whatsapp_notification_template_name
        )
        if (
            contact.channel is not ManagerContactChannel.WHATSAPP
            or template_name is None
        ):
            return None

        return OutboundTemplate(
            name=template_name,
            language_code=to_whatsapp_template_language(contact.language),
        )

    def _missing_provider(self, contact: ManagerContact) -> DeliveryErrorText | None:
        settings: AppSettings = self._app_settings
        if contact.channel is ManagerContactChannel.TELEGRAM:
            if settings.telegram_platform_bot_token is None:
                return DeliveryErrorText(
                    "TELEGRAM_PLATFORM_BOT_TOKEN is not configured."
                )

            return None

        if contact.channel is ManagerContactChannel.WHATSAPP:
            if (
                settings.whatsapp_notification_phone_number_id is None
                or settings.whatsapp_notification_template_name is None
            ):
                return DeliveryErrorText(
                    "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID or "
                    "WHATSAPP_NOTIFICATION_TEMPLATE is not configured."
                )

            return None

        if settings.environment is DeploymentEnvironment.PRODUCTION:
            return DeliveryErrorText(
                f"No {contact.channel.value} provider is configured for staff "
                "notifications."
            )

        return None
