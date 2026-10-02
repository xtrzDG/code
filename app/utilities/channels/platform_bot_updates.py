"""The parts of a platform bot update that the staff bot acts on."""

from typing import NamedTuple

from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_identifier,
    read_object,
    read_text,
)
from app.utilities.localization.language_tags import parse_language_tag

PRIVATE_CHAT_TYPE: str = "private"
FALLBACK_LANGUAGE: LanguageTag = LanguageTag("en")


class StaffBotMessage(NamedTuple):
    """
    A text a person wrote to the platform bot in a private chat (the text
    is raw input: the bot parses the command itself).
    """

    update_id: ProviderMessageId | None
    chat_id: ChannelUserId
    text: str
    sender_language: LanguageTag


def read_staff_bot_message(body: bytes) -> StaffBotMessage | None:
    """
    The staff message of an update; None for anything else (no text, a
    group chat, another bot, an edit, a malformed body).
    """

    update: JsonObject = parse_json_object(body) or {}
    message: JsonObject = read_object(update, "message") or {}
    chat: JsonObject = read_object(message, "chat") or {}
    sender: JsonObject = read_object(message, "from") or {}
    chat_id: str | None = read_identifier(chat, "id")
    text: str | None = read_text(message, "text")
    if (
        chat_id is None
        or text is None
        or read_text(chat, "type") != PRIVATE_CHAT_TYPE
        or read_flag(sender, "is_bot")
    ):
        return None

    update_id: str | None = read_identifier(update, "update_id")
    return StaffBotMessage(
        update_id=None if update_id is None else ProviderMessageId(update_id),
        chat_id=ChannelUserId(chat_id),
        text=text,
        sender_language=read_sender_language(sender),
    )


def read_sender_language(sender: JsonObject) -> LanguageTag:
    """The language of the sender's Telegram app, English when unknown."""

    raw_language: str | None = read_text(sender, "language_code")
    if raw_language is None:
        return FALLBACK_LANGUAGE

    try:
        return parse_language_tag(raw_language)
    except UnsupportedLanguageError:
        return FALLBACK_LANGUAGE
