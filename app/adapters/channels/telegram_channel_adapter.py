import logging
from functools import partial

from app.adapters.channels.telegram_tap_updates import TelegramTapUpdates
from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.channels import ChannelAdapterContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.domain.reply_choices import ReplyChoices
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
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
    TelegramCallbackQueryId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.attachment_reading import has_content
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.choice_delivery import send_with_choices, split_reply
from app.utilities.channels.choice_payloads import telegram_inline_keyboard
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_identifier,
    read_object,
    read_text,
)
from app.utilities.channels.skipped_webhook_parts import log_skipped_parts
from app.utilities.channels.telegram_attachments import read_telegram_attachments
from app.utilities.channels.telegram_messages import read_sender_name, tap_message
from app.utilities.channels.telegram_taps import TelegramTap, chosen_text, read_tap
from app.utilities.channels.telegram_update_kinds import update_kind
from app.utilities.channels.webhook_signatures import is_matching_telegram_secret
from app.utilities.conversations.reply_choices_text import number_the_options
from app.utilities.security.key_ring import key_ring
from app.utilities.sharing.acquisition_sources import read_start_payload

LOGGER: logging.Logger = logging.getLogger(__name__)
PLATFORM_NAME: str = "Telegram"
# Telegram counts the 4096-character limit of sendMessage in UTF-16 units.
TELEGRAM_MESSAGE_LIMIT: int = 4096
PRIVATE_CHAT_TYPE: str = "private"


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
        self._tap_updates: TelegramTapUpdates = TelegramTapUpdates(
            telegram_client, app_settings
        )

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
        tap: TelegramTap | None = read_tap(update)
        if tap is not None:
            return [tap_message(tap)]

        message: JsonObject | None = (
            None if update is None else read_object(update, "message")
        )
        if message is None:
            log_skipped_parts(LOGGER, PLATFORM_NAME, [update_kind(update)])
            return []

        chat: JsonObject = read_object(message, "chat") or {}
        sender: JsonObject = read_object(message, "from") or {}
        chat_id: str | None = read_identifier(chat, "id")
        if (
            chat_id is None
            or read_text(chat, "type") != PRIVATE_CHAT_TYPE
            or read_flag(sender, "is_bot")
        ):
            log_skipped_parts(LOGGER, PLATFORM_NAME, ["message:not a private chat"])
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
            log_skipped_parts(LOGGER, PLATFORM_NAME, ["message:without content"])
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

    def split(
        self, text: MessageText, choices: ReplyChoices | None = None
    ) -> list[MessageText]:
        return [
            MessageText(part)
            for part in split_reply(str(text), TELEGRAM_MESSAGE_LIMIT, choices)
        ]

    def send(
        self,
        target: ChannelDeliveryTarget,
        text: MessageText,
        choices: ReplyChoices | None = None,
    ) -> ChannelSendReceipt:
        """
        Options go as an inline keyboard under the last part; a bot whose
        taps cannot reach the platform gets them as a numbered list.
        """

        bot_token: ChannelSecret | None = target.credential
        if bot_token is None:
            raise ExternalServiceError(
                "The Telegram bot of this business is not connected."
            )

        def send_part(
            part: str, keyboard: JsonObject | None = None
        ) -> ProviderMessageId | None:
            return self._telegram_client.send_message(
                bot_token, target.channel_user_id, OutboundMessagePart(part), keyboard
            )

        parts: list[MessageText] = self.split(text, choices)
        provider_message_id: ProviderMessageId | None = None
        for index, part in enumerate(parts):
            if choices is None or index < len(parts) - 1:
                provider_message_id = send_part(str(part))
            elif self._tap_updates.ensure(bot_token):
                provider_message_id = send_with_choices(
                    PLATFORM_NAME,
                    str(part),
                    choices,
                    partial(send_part, keyboard=telegram_inline_keyboard(choices)),
                    send_part,
                )
            else:
                provider_message_id = send_part(number_the_options(str(part), choices))

        return ChannelSendReceipt(
            delivered=DeliveredMessageCount(len(parts)),
            provider_message_id=provider_message_id,
        )

    def acknowledge_taps(
        self,
        payload: ChannelWebhookPayload,
        channel_secret: ChannelSecret | None,
    ) -> None:
        """
        Answer the tap (the button stops showing progress), then keep the
        chosen option as the tapped message's last line without its
        buttons, so nothing is tapped twice. Best effort, logged.
        """

        tap: TelegramTap | None = read_tap(parse_json_object(payload.body))
        if tap is None or channel_secret is None:
            return

        try:
            self._telegram_client.answer_callback_query(
                channel_secret, TelegramCallbackQueryId(tap.callback_query_id)
            )
            if tap.message_id is not None and tap.message_text is not None:
                self._telegram_client.edit_message_text(
                    channel_secret,
                    ProviderMessageId(f"{tap.chat_id}:{tap.message_id}"),
                    OutboundMessagePart(chosen_text(tap.message_text, tap.label)),
                )
        except ApplicationError as error:
            LOGGER.info("A Telegram button tap was not acknowledged: %s", error)

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
