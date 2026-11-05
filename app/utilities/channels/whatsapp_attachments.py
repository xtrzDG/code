"""
Attachments of a WhatsApp Cloud API message (webhook `messages[]`, by
`type`): voice notes and audio files, photos, places, contact cards,
stickers and everything else a customer can send (video, documents, an
"unsupported" message) as one the assistant asks to write about instead.
Reactions and system notices are not messages to answer and have none.
"""

from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import InboundAttachment
from app.utilities.channels.attachment_reading import (
    build_location_attachment,
    build_media_attachment,
    build_unreadable_attachment,
)
from app.utilities.channels.json_values import (
    JsonObject,
    read_identifier,
    read_integer,
    read_number,
    read_object,
    read_text,
)

MEDIA_KINDS: dict[str, AttachmentKind] = {
    "audio": AttachmentKind.AUDIO,
    "image": AttachmentKind.IMAGE,
}
UNREADABLE_KINDS: dict[str, AttachmentKind] = {
    "contacts": AttachmentKind.CONTACT,
    "sticker": AttachmentKind.STICKER,
    "video": AttachmentKind.OTHER,
    "document": AttachmentKind.OTHER,
    "unsupported": AttachmentKind.OTHER,
    "order": AttachmentKind.OTHER,
}


def read_whatsapp_attachments(message: JsonObject) -> list[InboundAttachment]:
    message_type: str | None = read_text(message, "type")
    if message_type is None:
        return []

    if message_type in MEDIA_KINDS:
        media: JsonObject = read_object(message, message_type) or {}
        return [
            build_media_attachment(
                MEDIA_KINDS[message_type],
                read_identifier(media, "id"),
                read_text(media, "mime_type"),
                read_text(media, "caption"),
                read_integer(media, "file_size"),
            )
        ]

    if message_type == "location":
        place: JsonObject = read_object(message, "location") or {}
        return [
            build_location_attachment(
                read_number(place, "latitude"),
                read_number(place, "longitude"),
                read_text(place, "name"),
                read_text(place, "address"),
            )
        ]

    if message_type in UNREADABLE_KINDS:
        body: JsonObject = read_object(message, message_type) or {}
        return [
            build_unreadable_attachment(
                UNREADABLE_KINDS[message_type], read_text(body, "caption")
            )
        ]

    return []
