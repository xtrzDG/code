"""A channel sender that records reminders and can fail one channel on demand."""

from collections.abc import Callable

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag


class RecordingChannelSender(ChannelMessageSenderFacilitatorContract):
    """Records proactive messages; channels listed as failing raise."""

    def __init__(self, failing_channels: frozenset[ChannelKind] = frozenset()) -> None:
        self.failing_channels: set[ChannelKind] = set(failing_channels)
        self.attempts: list[ChannelKind] = []
        self.sent: list[tuple[BusinessId, ChannelKind, ChannelUserId, MessageText]] = []
        self.templates: list[tuple[BusinessId, ChannelUserId, str, str, list[str]]] = []
        self.on_send: Callable[[], None] | None = None

    def send(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
        text: MessageText,
    ) -> None:
        self.attempts.append(channel)
        if self.on_send is not None:
            self.on_send()

        if channel in self.failing_channels:
            raise ExternalServiceError(f"The {channel.value} channel is not connected.")

        self.sent.append((business_id, channel, channel_user_id, text))

    def send_whatsapp_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language: LanguageTag,
        body_parameters: list[MessageText],
    ) -> None:
        self.attempts.append(ChannelKind.WHATSAPP)
        if ChannelKind.WHATSAPP in self.failing_channels:
            raise ExternalServiceError("The whatsapp channel is not connected.")

        self.templates.append(
            (
                business_id,
                channel_user_id,
                str(template_name),
                str(language),
                [str(parameter) for parameter in body_parameters],
            )
        )

    def send_whatsapp_template_in_language(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        raise AssertionError("Reminders follow the customer's language.")
