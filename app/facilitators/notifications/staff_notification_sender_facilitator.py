import logging

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import WhatsAppTemplateAdapterContract
from app.contracts.facilitators import StaffNotificationSenderContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.channels.strings import OutboundMessagePart, ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.message_chunks import split_message_text

logger: logging.Logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT: int = 4096
FALLBACK_TEMPLATE_LANGUAGE: WhatsAppTemplateLanguageCode = WhatsAppTemplateLanguageCode(
    "en"
)
VISIBLE_ADDRESS_CHARACTERS: int = 3


class StaffNotificationSenderFacilitator(StaffNotificationSenderContract):
    """
    Sends staff notifications (concept section 1) for the outbox worker.

    - Telegram: the platform bot (TELEGRAM_PLATFORM_BOT_TOKEN) writes to the
      chat linked with "/start <code>"; free of charge.
    - WhatsApp: the approved template the message was queued with (one body
      parameter: the text) from the platform number
      WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID, in English when Meta refuses
      the staff member's language.
    - E-mail and SMS have no provider yet: outside production the
      notification is logged (without its text) and counts as delivered; in
      production it cannot be delivered.

    Errors are raised for the outbox to classify (retry or give up).
    """

    def __init__(
        self,
        telegram_client: TelegramBotApiClientContract,
        whatsapp_templates: WhatsAppTemplateAdapterContract,
        app_settings: AppSettings,
    ) -> None:
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._whatsapp_templates: WhatsAppTemplateAdapterContract = whatsapp_templates
        self._app_settings: AppSettings = app_settings

    def split(self, contact: ManagerContact, text: MessageText) -> list[MessageText]:
        if contact.channel is ManagerContactChannel.TELEGRAM:
            return [
                MessageText(part)
                for part in split_message_text(str(text), TELEGRAM_MESSAGE_LIMIT)
            ]

        return [text]

    def send(
        self,
        contact: ManagerContact,
        text: MessageText,
        template: OutboundTemplate | None,
    ) -> ProviderMessageId | None:
        if contact.channel is ManagerContactChannel.TELEGRAM:
            return self._send_by_telegram(contact, text)

        if contact.channel is ManagerContactChannel.WHATSAPP:
            return self._send_by_whatsapp(contact, text, template)

        return self._send_without_provider(contact)

    def _send_by_telegram(
        self,
        contact: ManagerContact,
        text: MessageText,
    ) -> ProviderMessageId | None:
        bot_token: PlatformSecret | None = (
            self._app_settings.telegram_platform_bot_token
        )
        if bot_token is None:
            raise DeliveryNotConfiguredError(
                "TELEGRAM_PLATFORM_BOT_TOKEN is not configured."
            )

        return self._telegram_client.send_message(
            bot_token,
            ChannelUserId(str(contact.address)),
            OutboundMessagePart(str(text)),
        )

    def _send_by_whatsapp(
        self,
        contact: ManagerContact,
        text: MessageText,
        template: OutboundTemplate | None,
    ) -> ProviderMessageId | None:
        phone_number_id: MetaObjectId | None = (
            self._app_settings.whatsapp_notification_phone_number_id
        )
        if phone_number_id is None or template is None:
            raise DeliveryNotConfiguredError(
                "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID or "
                "WHATSAPP_NOTIFICATION_TEMPLATE is not configured."
            )

        recipient = ChannelUserId(str(contact.address).removeprefix("+"))
        try:
            return self._whatsapp_templates.send_template(
                phone_number_id,
                recipient,
                template.name,
                template.language_code,
                [text],
            )
        except WhatsAppTemplateRejectedError:
            if template.language_code == FALLBACK_TEMPLATE_LANGUAGE:
                raise

            logger.warning(
                "Staff WhatsApp template in %s was refused; sending it in English.",
                template.language_code,
            )
            return self._whatsapp_templates.send_template(
                phone_number_id,
                recipient,
                template.name,
                FALLBACK_TEMPLATE_LANGUAGE,
                [text],
            )

    def _send_without_provider(self, contact: ManagerContact) -> None:
        masked_address: str = mask_address(str(contact.address))
        if self._app_settings.environment is DeploymentEnvironment.PRODUCTION:
            raise DeliveryNotConfiguredError(
                f"No {contact.channel.value} provider is configured for staff "
                "notifications."
            )

        logger.info(
            "Staff notification to %s by %s would be sent here (no provider "
            "outside production).",
            masked_address,
            contact.channel.value,
        )


def mask_address(address: str) -> str:
    """Last characters of an e-mail or phone; enough to tell staff apart."""

    if len(address) <= VISIBLE_ADDRESS_CHARACTERS:
        return "***"

    return "***" + address[-VISIBLE_ADDRESS_CHARACTERS:]
