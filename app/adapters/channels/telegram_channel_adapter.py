from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import ChannelAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelInboundMessage,
    ChannelSendReceipt,
    ChannelWebhookPayload,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
)
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.constrained_strings import TelegramWebhookSecret
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_identifier,
    read_object,
    read_text,
)
from app.utilities.channels.message_chunks import split_message_text
from app.utilities.channels.webhook_signatures import (
    derive_telegram_webhook_secret,
    is_matching_secret,
)

# Telegram counts the 4096-character limit of sendMessage in UTF-16 units.
TELEGRAM_MESSAGE_LIMIT: int = 4096
PRIVATE_CHAT_TYPE: str = "private"
MAX_CONTACT_NAME_LENGTH: int = 128


class TelegramChannelAdapter(ChannelAdapterContract):
    """
    Telegram bot of one business (Bot API webhooks).

    Every bot's webhook carries the secret derived from its token
    (X-Telegram-Bot-Api-Secret-Token). Only private chats with people are
    answered; a contact the customer shares about themselves gives their
    phone number (stored as E.164).
    """

    def __init__(
        self,
        telegram_client: TelegramBotApiClientContract,
        phone_number_parser: PhoneNumberParserContract,
        app_settings: AppSettings,
    ) -> None:
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._app_settings: AppSettings = app_settings

    def verify_signature(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        encryption_key = self._app_settings.encryption_key
        if channel_secret is None or encryption_key is None:
            raise AuthenticationRequiredError(
                "This Telegram webhook cannot be verified."
            )

        expected_secret: TelegramWebhookSecret = derive_telegram_webhook_secret(
            encryption_key,
            channel_secret,
        )
        if not is_matching_secret(str(expected_secret), payload.signature_header):
            raise AuthenticationRequiredError(
                "The Telegram webhook secret token is missing or wrong."
            )

    def parse_webhook(
        self,
        payload: ChannelWebhookPayload,
    ) -> list[ChannelInboundMessage]:
        update: JsonObject | None = parse_json_object(payload.body)
        message: JsonObject | None = (
            None if update is None else read_object(update, "message")
        )
        if message is None:
            return []

        chat: JsonObject = read_object(message, "chat") or {}
        sender: JsonObject = read_object(message, "from") or {}
        chat_id: str | None = read_identifier(chat, "id")
        if (
            chat_id is None
            or read_text(chat, "type") != PRIVATE_CHAT_TYPE
            or read_flag(sender, "is_bot")
        ):
            return []

        phone_number: E164PhoneNumber | None = self._read_own_phone_number(
            message,
            sender,
        )
        text: str | None = read_text(message, "text")
        if text is None and phone_number is not None:
            text = str(phone_number)

        if text is None:
            return []

        message_id: str | None = read_identifier(message, "message_id")
        return [
            ChannelInboundMessage(
                channel=ChannelKind.TELEGRAM,
                channel_user_id=ChannelUserId(chat_id),
                text=MessageText(text),
                contact_name=read_sender_name(sender),
                contact_phone_number=phone_number,
                provider_message_id=(
                    None
                    if message_id is None
                    else ProviderMessageId(f"{chat_id}:{message_id}")
                ),
            )
        ]

    def split(self, text: MessageText) -> list[MessageText]:
        return [
            MessageText(part)
            for part in split_message_text(str(text), TELEGRAM_MESSAGE_LIMIT)
        ]

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
    ) -> ChannelSendReceipt:
        if target.credential is None:
            raise ExternalServiceError(
                "The Telegram bot of this business is not connected."
            )

        parts: list[MessageText] = self.split(text)
        provider_message_id: ProviderMessageId | None = None
        for part in parts:
            provider_message_id = self._telegram_client.send_message(
                target.credential,
                target.channel_user_id,
                OutboundMessagePart(str(part)),
            )

        return ChannelSendReceipt(
            delivered=DeliveredMessageCount(len(parts)),
            provider_message_id=provider_message_id,
        )

    def _read_own_phone_number(
        self,
        message: JsonObject,
        sender: JsonObject,
    ) -> E164PhoneNumber | None:
        """Phone of a shared contact, only when it is the sender's own."""

        contact: JsonObject | None = read_object(message, "contact")
        if contact is None:
            return None

        contact_user_id: str | None = read_identifier(contact, "user_id")
        sender_id: str | None = read_identifier(sender, "id")
        raw_phone_number: str | None = read_text(contact, "phone_number")
        if (
            raw_phone_number is None
            or contact_user_id is None
            or contact_user_id != sender_id
        ):
            return None

        return parse_messaging_phone_number(self._phone_number_parser, raw_phone_number)


def read_sender_name(sender: JsonObject) -> ContactName | None:
    """First and last name of a Telegram user, as they set them."""

    name_parts: list[str] = [
        part.strip()
        for part in (read_text(sender, "first_name"), read_text(sender, "last_name"))
        if part is not None
    ]
    full_name: str = " ".join(name_parts)[:MAX_CONTACT_NAME_LENGTH].strip()
    return None if full_name == "" else ContactName(full_name)
