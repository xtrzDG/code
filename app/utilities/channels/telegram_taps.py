"""
A tap on a button of a business bot's inline keyboard (Telegram
`callback_query`), read back as the option's text, and what the bot does
to acknowledge it: the tapped message keeps the chosen option as its last
line and loses its buttons, so the chat shows what was chosen and nothing
can be tapped twice.
"""

from dataclasses import dataclass
from typing import cast

from app.utilities.channels.choice_payloads import TELEGRAM_INDEX_PREFIX
from app.utilities.channels.json_values import (
    JsonObject,
    read_flag,
    read_identifier,
    read_object,
    read_objects,
    read_text,
)

CHOSEN_MARK: str = "✓"
PRIVATE_CHAT_TYPE: str = "private"


@dataclass(frozen=True)
class TelegramTap:
    """One tap of a customer in a private chat (technical record)."""

    callback_query_id: str
    chat_id: str
    sender: JsonObject
    label: str
    message_id: str | None
    message_text: str | None


def read_tap(update: JsonObject | None) -> TelegramTap | None:
    """
    The tap of a `callback_query` update in a private chat with a person,
    with the label of the tapped button; None for anything else (a tap on
    a message too old to be read back still gives its data as the label).
    """

    query: JsonObject | None = (
        None if update is None else read_object(update, "callback_query")
    )
    if query is None:
        return None

    message: JsonObject = read_object(query, "message") or {}
    chat: JsonObject = read_object(message, "chat") or {}
    sender: JsonObject = read_object(query, "from") or {}
    query_id: str | None = read_text(query, "id")
    chat_id: str | None = read_identifier(chat, "id")
    data: str | None = read_text(query, "data")
    if (
        query_id is None
        or chat_id is None
        or data is None
        or read_text(chat, "type") != PRIVATE_CHAT_TYPE
        or read_flag(sender, "is_bot")
    ):
        return None

    label: str | None = button_text(message, data)
    if label is None or not label.strip():
        return None

    return TelegramTap(
        callback_query_id=query_id,
        chat_id=chat_id,
        sender=sender,
        label=label.strip(),
        message_id=read_identifier(message, "message_id"),
        message_text=read_text(message, "text"),
    )


def button_text(message: JsonObject, data: str) -> str | None:
    """The text of the keyboard button that carries `data`, else the data."""

    markup: JsonObject = read_object(message, "reply_markup") or {}
    keyboard: object = markup.get("inline_keyboard")
    for row in cast(list[object], keyboard) if isinstance(keyboard, list) else []:
        for button in read_objects({"row": row}, "row"):
            if read_text(button, "callback_data") == data:
                return read_text(button, "text")

    return None if data.startswith(TELEGRAM_INDEX_PREFIX) else data


def chosen_text(message_text: str, label: str) -> str:
    """The tapped message with the chosen option as its last line."""

    return f"{message_text.rstrip()}\n\n{CHOSEN_MARK} {label}"
