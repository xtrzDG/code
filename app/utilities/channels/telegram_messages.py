"""Pieces of a Telegram customer's message: who sent it, and a tap as text."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.channels.json_values import JsonObject, read_text
from app.utilities.channels.telegram_taps import TelegramTap

MAX_CONTACT_NAME_LENGTH: int = 128
# Marks the id of a tap among the "<chat id>:<message id>" ids of messages.
TAP_ID_MARK: str = "tap-"


def read_sender_name(sender: JsonObject) -> ContactName | None:
    """First and last name of a Telegram user, as they set them."""

    name_parts: list[str] = [
        part.strip()
        for part in (read_text(sender, "first_name"), read_text(sender, "last_name"))
        if part is not None
    ]
    full_name: str = " ".join(name_parts)[:MAX_CONTACT_NAME_LENGTH].strip()
    return None if full_name == "" else ContactName(full_name)


def tap_message(tap: TelegramTap) -> ChannelInboundMessage:
    """
    A tapped button as the customer's message: the option's text, under an
    id of its own (one per tap, so a redelivered update is stored once).
    """

    return ChannelInboundMessage(
        channel=ChannelKind.TELEGRAM,
        channel_user_id=ChannelUserId(tap.chat_id),
        text=MessageText(tap.label),
        contact_name=read_sender_name(tap.sender),
        provider_message_id=ProviderMessageId(
            f"{tap.chat_id}:{TAP_ID_MARK}{tap.callback_query_id}"
        ),
    )
