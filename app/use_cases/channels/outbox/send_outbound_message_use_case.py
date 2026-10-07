from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import (
    ChannelAdapterContract,
    WhatsAppTemplateAdapterContract,
)
from app.contracts.facilitators import StaffNotificationSenderContract
from app.contracts.invoicing import BillingEmailAttachmentsFacilitatorContract
from app.contracts.notifications import PushNotificationSenderContract
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import OutboundAttempt
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.strings import ProviderMessageId
from app.use_cases.channels.outbox.customer_templates import (
    build_template_usage_event,
    route_customer_template,
)
from app.use_cases.channels.outbox.outbound_expiry import expired_attempt
from app.use_cases.channels.outbox.outbound_routes import (
    OutboundRoute,
    route_billing_email,
    route_customer_reply,
    route_push_notification,
    route_staff_notification,
)
from app.utilities.channels.delivery_targets import build_whatsapp_usage_event
from app.utilities.deliveries.retry_policy import (
    classify_delivery_error,
    describe_delivery_error,
    explain_delivery_error,
    read_retry_after,
)


class SendOutboundMessageUseCase(
    UseCaseContract[OutboundMessageDocument, OutboundAttempt]
):
    """
    One send attempt of an outbox message: its parts (long texts are split
    at the channel's limit) go out one by one, starting after the parts an
    earlier attempt delivered, so a retry never repeats a part the customer
    already has. A failure stops the attempt and is classified (rate
    limited, temporary, refused, credential refused, no provider) for the
    retry decision. A message past its `send_before` is not sent at all
    (given up as EXPIRED). WhatsApp replies are metered per delivered
    part, a WhatsApp template to a customer (outside the 24-hour window)
    as one template. An e-mail to the billing contact attaches its invoice
    PDFs, made at each attempt.
    """

    def __init__(
        self,
        telegram_adapter: ChannelAdapterContract,
        whatsapp_adapter: ChannelAdapterContract,
        messenger_adapter: ChannelAdapterContract,
        instagram_adapter: ChannelAdapterContract,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        staff_sender: StaffNotificationSenderContract,
        push_sender: PushNotificationSenderContract,
        usage_event_repo: UsageEventRepoContract,
        wall_clock: WallClock[Microseconds],
        whatsapp_templates: WhatsAppTemplateAdapterContract,
        billing_attachments: BillingEmailAttachmentsFacilitatorContract,
    ) -> None:
        self._billing_attachments: BillingEmailAttachmentsFacilitatorContract = (
            billing_attachments
        )
        self._whatsapp_templates: WhatsAppTemplateAdapterContract = whatsapp_templates
        self._adapters: dict[ChannelKind, ChannelAdapterContract] = {
            ChannelKind.TELEGRAM: telegram_adapter,
            ChannelKind.WHATSAPP: whatsapp_adapter,
            ChannelKind.MESSENGER: messenger_adapter,
            ChannelKind.INSTAGRAM: instagram_adapter,
        }
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._staff_sender: StaffNotificationSenderContract = staff_sender
        self._push_sender: PushNotificationSenderContract = push_sender
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OutboundMessageDocument) -> OutboundAttempt:
        now: Microseconds = self._wall_clock.now_unix()
        if input_data.send_before is not None and now > input_data.send_before:
            return expired_attempt(input_data, now)

        delivered: int = int(input_data.delivered_parts)
        provider_message_id: ProviderMessageId | None = input_data.provider_message_id
        route: OutboundRoute | None = None
        try:
            route = self._route(input_data)
            while delivered < len(route.parts):
                provider_message_id = (
                    route.sender_of(delivered)(route.parts[delivered])
                    or provider_message_id
                )
                delivered += 1
        except ApplicationError as error:
            self._meter(input_data, delivered)
            return OutboundAttempt(
                message=input_data,
                channel=None if route is None else route.channel,
                delivered_parts=DeliveredMessageCount(delivered),
                provider_message_id=provider_message_id,
                failure=classify_delivery_error(error),
                reason=explain_delivery_error(error),
                error=describe_delivery_error(error),
                retry_after_seconds=read_retry_after(error),
                attempted_at=self._wall_clock.now_unix(),
            )

        self._meter(input_data, delivered)
        return OutboundAttempt(
            message=input_data,
            channel=route.channel,
            delivered_parts=DeliveredMessageCount(delivered),
            provider_message_id=provider_message_id,
            attempted_at=self._wall_clock.now_unix(),
        )

    def _route(self, message: OutboundMessageDocument) -> OutboundRoute:
        if message.customer is not None and message.template is not None:
            return route_customer_template(
                message,
                message.customer,
                message.template,
                self._channel_repo,
                self._whatsapp_templates,
            )

        if message.customer is not None:
            return route_customer_reply(
                message,
                message.customer,
                self._channel_repo,
                self._secret_cipher,
                self._adapters,
            )

        if message.staff_contact is not None and message.billing_documents:
            return route_billing_email(
                message,
                message.staff_contact,
                message.billing_documents,
                self._staff_sender,
                self._billing_attachments,
            )

        if message.staff_contact is not None:
            return route_staff_notification(
                message, message.staff_contact, self._staff_sender
            )

        if message.push is not None:
            return route_push_notification(message, message.push, self._push_sender)

        raise ValidationFailedError("The outbox message names no recipient.")

    def _meter(self, message: OutboundMessageDocument, delivered: int) -> None:
        """
        WhatsApp replies sent in this attempt (concept usage wa_reply), or
        the template sent (wa_template).
        """

        sent_now: int = delivered - int(message.delivered_parts)
        if (
            sent_now <= 0
            or message.customer is None
            or message.customer.channel is not ChannelKind.WHATSAPP
        ):
            return

        if message.template is not None:
            self._usage_event_repo.append(
                build_template_usage_event(message, self._wall_clock.now_unix())
            )
            return

        self._usage_event_repo.append(
            build_whatsapp_usage_event(
                message.business_id,
                message.conversation_id,
                DeliveredMessageCount(sent_now),
                self._wall_clock.now_unix(),
            )
        )
