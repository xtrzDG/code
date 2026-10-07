import logging
from collections.abc import Sequence

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import WhatsAppTemplateAdapterContract
from app.contracts.facilitators import StaffNotificationSenderContract
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    ValidationFailedError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.channels.strings import OutboundMessagePart, ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.channels.message_chunks import split_message_text
from app.utilities.notifications.staff_email import StaffEmail, build_staff_email

logger: logging.Logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT: int = 4096
FALLBACK_TEMPLATE_LANGUAGE: WhatsAppTemplateLanguageCode = WhatsAppTemplateLanguageCode(
    "en"
)
VISIBLE_ADDRESS_CHARACTERS: int = 3
# Meta refuses template parameters with line breaks, tabs or more than four
# spaces in a row: the lines are joined with this separator.
TEMPLATE_LINE_SEPARATOR: str = " · "


class StaffNotificationSenderFacilitator(StaffNotificationSenderContract):
    """
    Sends staff notifications (concept section 1) for the outbox worker.

    - Telegram: the platform bot (TELEGRAM_PLATFORM_BOT_TOKEN) writes to the
      chat linked with "/start <code>"; free of charge.
    - WhatsApp: the approved template the message was queued with (its own
      body parameters, else one: the text; each on one line) from the
      platform number
      WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID, in English when Meta refuses
      the staff member's language.
    - E-mail: SMTP (the server of login codes), the first line as subject,
      a plain and an HTML body with the link as a button; files attached
      when the message carries them (invoice and receipt PDFs).
    - SMS: Twilio (the account of login codes), the text as it is.
    - Without the provider of a contact's channel the notification is
      logged (without its text) and counts as delivered outside
      production; in production it cannot be delivered.

    Errors are raised for the outbox to classify (retry or give up).
    """

    def __init__(
        self,
        telegram_client: TelegramBotApiClientContract,
        whatsapp_templates: WhatsAppTemplateAdapterContract,
        app_settings: AppSettings,
        email_client: EmailSenderClientContract | None = None,
        sms_client: SmsMessagingClientContract | None = None,
    ) -> None:
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._whatsapp_templates: WhatsAppTemplateAdapterContract = whatsapp_templates
        self._app_settings: AppSettings = app_settings
        self._email_client: EmailSenderClientContract | None = email_client
        self._sms_client: SmsMessagingClientContract | None = sms_client

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

        if contact.channel is ManagerContactChannel.EMAIL and self._email_client:
            email: StaffEmail = build_staff_email(text)
            self._email_client.send_email(
                EmailAddress(str(contact.address)),
                email.subject,
                email.text_body,
                email.html_body,
            )
            return None

        if contact.channel is ManagerContactChannel.SMS and self._sms_client:
            self._sms_client.send_sms(
                E164PhoneNumber(str(contact.address)), SmsMessageText(str(text))
            )
            return None

        self._send_without_provider(contact)
        return None

    def send_with_files(
        self,
        contact: ManagerContact,
        text: MessageText,
        attachments: Sequence[EmailAttachment],
    ) -> None:
        if contact.channel is not ManagerContactChannel.EMAIL:
            raise ValidationFailedError("Only e-mail carries attached files.")

        if self._email_client is None:
            self._send_without_provider(contact)
            return

        email: StaffEmail = build_staff_email(text)
        self._email_client.send_email(
            EmailAddress(str(contact.address)),
            email.subject,
            email.text_body,
            email.html_body,
            attachments,
        )

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
        parameters: list[MessageText] = [
            MessageText(one_line(str(parameter)))
            for parameter in (template.body_parameters or [text])
        ]
        try:
            return self._whatsapp_templates.send_template(
                phone_number_id,
                recipient,
                template.name,
                template.language_code,
                parameters,
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
                parameters,
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


def one_line(text: str) -> str:
    """The lines of a text joined into one, spaces collapsed (WhatsApp)."""

    lines: list[str] = [" ".join(line.split()) for line in text.splitlines()]
    return TEMPLATE_LINE_SEPARATOR.join(line for line in lines if line)
