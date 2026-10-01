import logging

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import WhatsAppTemplateAdapterContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import OutboundMessagePart
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.channels.message_chunks import split_message_text

logger: logging.Logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT: int = 4096
FALLBACK_TEMPLATE_LANGUAGE: WhatsAppTemplateLanguageCode = WhatsAppTemplateLanguageCode(
    "en"
)
VISIBLE_ADDRESS_CHARACTERS: int = 3


class ManagerNotificationFacilitator(ManagerNotificationFacilitatorContract):
    """
    Notify staff about handoffs, bookings and leads (concept section 1).

    - Telegram: the platform bot (TELEGRAM_PLATFORM_BOT_TOKEN) writes to the
      chat linked with "/start <code>"; free of charge.
    - WhatsApp: the approved template WHATSAPP_NOTIFICATION_TEMPLATE (one
      body parameter: the text) from the platform number
      WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID, in the staff member's language
      and in English when that translation is missing.
    - E-mail and SMS have no provider yet: outside production the
      notification is logged (without its text) and counts as delivered; in
      production it is reported as not delivered.

    Delivery problems are logged and reported as False, never raised.
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

    def notify(self, contact: ManagerContact, text: MessageText) -> bool:
        try:
            if contact.channel is ManagerContactChannel.TELEGRAM:
                return self._notify_by_telegram(contact, text)

            if contact.channel is ManagerContactChannel.WHATSAPP:
                return self._notify_by_whatsapp(contact, text)

            return self._notify_without_provider(contact)
        except Exception:
            logger.exception(
                "Staff notification through %s failed.",
                contact.channel.value,
            )
            return False

    def _notify_by_telegram(self, contact: ManagerContact, text: MessageText) -> bool:
        bot_token: PlatformSecret | None = (
            self._app_settings.telegram_platform_bot_token
        )
        if bot_token is None:
            logger.warning(
                "Staff Telegram notification skipped: "
                "TELEGRAM_PLATFORM_BOT_TOKEN is not configured."
            )
            return False

        for part in split_message_text(str(text), TELEGRAM_MESSAGE_LIMIT):
            self._telegram_client.send_message(
                bot_token,
                ChannelUserId(str(contact.address)),
                OutboundMessagePart(part),
            )

        return True

    def _notify_by_whatsapp(self, contact: ManagerContact, text: MessageText) -> bool:
        phone_number_id: MetaObjectId | None = (
            self._app_settings.whatsapp_notification_phone_number_id
        )
        template_name: WhatsAppTemplateName | None = (
            self._app_settings.whatsapp_notification_template_name
        )
        if phone_number_id is None or template_name is None:
            logger.warning(
                "Staff WhatsApp notification skipped: "
                "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID or "
                "WHATSAPP_NOTIFICATION_TEMPLATE is not configured."
            )
            return False

        recipient = ChannelUserId(str(contact.address).removeprefix("+"))
        language_code: WhatsAppTemplateLanguageCode = to_whatsapp_template_language(
            contact.language
        )
        try:
            self._whatsapp_templates.send_template(
                phone_number_id, recipient, template_name, language_code, [text]
            )
        except Exception:
            if language_code == FALLBACK_TEMPLATE_LANGUAGE:
                raise

            logger.warning(
                "Staff WhatsApp template in %s failed; retrying in English.",
                language_code,
            )
            self._whatsapp_templates.send_template(
                phone_number_id,
                recipient,
                template_name,
                FALLBACK_TEMPLATE_LANGUAGE,
                [text],
            )

        return True

    def _notify_without_provider(self, contact: ManagerContact) -> bool:
        masked_address: str = mask_address(str(contact.address))
        if self._app_settings.environment is DeploymentEnvironment.PRODUCTION:
            logger.warning(
                "Staff notification to %s by %s not sent: no provider is configured.",
                masked_address,
                contact.channel.value,
            )
            return False

        logger.info(
            "Staff notification to %s by %s would be sent here (no provider "
            "outside production).",
            masked_address,
            contact.channel.value,
        )
        return True


def mask_address(address: str) -> str:
    """Last characters of an e-mail or phone; enough to tell staff apart."""

    if len(address) <= VISIBLE_ADDRESS_CHARACTERS:
        return "***"

    return "***" + address[-VISIBLE_ADDRESS_CHARACTERS:]
