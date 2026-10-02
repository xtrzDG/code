"""Narrow side effects towards people outside the system."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode


class OtpDeliveryFacilitatorContract(FacilitatorContract, Protocol):
    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        """Channels this facilitator can deliver codes through right now."""
        raise NotImplementedError

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        """Send a login code. Raises ExternalServiceError when delivery fails."""
        raise NotImplementedError


class ManagerNotificationFacilitatorContract(FacilitatorContract, Protocol):
    def notify(self, notification: StaffNotification) -> bool:
        """
        Queue a staff notification in the outbox (the worker sends it through
        the platform Telegram bot, a WhatsApp template, e-mail or SMS, with
        retries). False when it cannot be delivered (no provider for the
        contact's channel) or could not be queued; never raises.
        """
        raise NotImplementedError


class StaffNotificationSenderContract(FacilitatorContract, Protocol):
    """The providers that carry staff notifications, one platform message at a time."""

    def split(self, contact: ManagerContact, text: MessageText) -> list[MessageText]:
        """The platform messages a notification goes out as, in order."""
        raise NotImplementedError

    def send(
        self,
        contact: ManagerContact,
        text: MessageText,
        template: OutboundTemplate | None,
    ) -> ProviderMessageId | None:
        """
        Send one part (WhatsApp: the template with the text as its
        parameter, in English when the contact's language is refused). The
        provider's message id when it names one. Raises
        DeliveryNotConfiguredError, ProviderRateLimitedError,
        ProviderRejectedMessageError or ExternalServiceError.
        """
        raise NotImplementedError


class ChannelMessageSenderFacilitatorContract(FacilitatorContract, Protocol):
    def send(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
        text: MessageText,
    ) -> None:
        """
        Send a proactive message (confirmation after a call, reminder) as
        free-form text; metered as one usage event of the channel.

        Raises ExternalServiceError when the channel is not connected or fails.
        """
        raise NotImplementedError

    def send_whatsapp_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language: LanguageTag,
        body_parameters: list[MessageText],
    ) -> None:
        """
        Send a Meta-approved template from the business's WhatsApp number
        (needed outside the 24-hour customer service window); metered as one
        WHATSAPP_TEMPLATE usage event.

        Raises ExternalServiceError when the channel is not connected or fails.
        """
        raise NotImplementedError

    def send_whatsapp_template_in_language(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        """
        Send a Meta-approved template in exactly the language it was approved
        in (one the owner named, so there is no English fallback) from the
        business's WhatsApp number; metered as one WHATSAPP_TEMPLATE usage
        event.

        Raises ExternalServiceError when the channel is not connected or fails.
        """
        raise NotImplementedError
