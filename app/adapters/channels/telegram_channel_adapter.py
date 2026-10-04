from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import ChannelAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
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
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.attachment_reading import has_content
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
from app.utilities.channels.telegram_attachments import read_telegram_attachments
from app.utilities.channels.webhook_signatures import is_matching_telegram_secret
from app.utilities.security.key_ring import key_ring
from app.utilities.sharing.acquisition_sources import read_start_payload

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
    phone number (stored as E.164). Voice notes, photos (with their
    captions), places and other files are attachments
    (`telegram_attachments`). The payload of a tagged link's
    "/start src_<tag>" is where the customer came from.
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
        keys: list[PlatformSecret] = key_ring(self._app_settings)
        if channel_secret is None or not keys:
            raise AuthenticationRequiredError(
                "This Telegram webhook cannot be verified."
            )

        if not is_matching_telegram_secret(
            keys, channel_secret, payload.signature_header
        ):
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
        attachments: list[InboundAttachment] = read_telegram_attachments(
            message, is_own_contact=phone_number is not None
        )
        # A tagged t.me link starts with "/start src_<tag>": the tag is kept
        # as the source, the assistant reads "/start".
        source, text = read_start_payload(read_text(message, "text") or "")
        if text == "" and phone_number is not None:
            text = str(phone_number)

        if not has_content(text, attachments):
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
                attachments=attachments,
                acquisition_source=source,
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

    def signal_typing(
        self,
        target: ChannelDeliveryTarget,
        replying_to: ProviderMessageId | None,
    ) -> None:
        """`sendChatAction` "typing" (shown for about 5 seconds)."""

        del replying_to
        if target.credential is None:
            return

        self._telegram_client.send_typing_action(
            target.credential, target.channel_user_id
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
