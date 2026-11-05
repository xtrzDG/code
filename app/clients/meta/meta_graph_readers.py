"""Reading the Graph API's answers: ids and usernames, invalid ones as None."""

from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
)
from app.utilities.channels.json_values import (
    JsonObject,
    read_identifier,
    read_objects,
    read_text,
)


def read_object_id(source: JsonObject, key: str) -> MetaObjectId | None:
    raw_id: str | None = read_identifier(source, key)
    if raw_id is None:
        return None

    try:
        return MetaObjectId(raw_id)
    except ValueError:
        return None


def read_page_username(source: JsonObject) -> MetaPageUsername | None:
    raw_username: str | None = read_text(source, "username")
    try:
        return None if raw_username is None else MetaPageUsername(raw_username)
    except ValueError:
        return None


def read_instagram_username(source: JsonObject) -> InstagramUsername | None:
    raw_username: str | None = read_text(source, "username")
    try:
        return None if raw_username is None else InstagramUsername(raw_username)
    except ValueError:
        return None


def read_whatsapp_message_id(body: JsonObject) -> ProviderMessageId | None:
    """The "wamid..." of a sent WhatsApp message (`messages[0].id`)."""

    messages: list[JsonObject] = read_objects(body, "messages")
    message_id: str | None = read_identifier(messages[0], "id") if messages else None
    return None if message_id is None else ProviderMessageId(message_id)
