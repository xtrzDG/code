"""
Attachments of a Messenger or Instagram message (`message.attachments[]`,
by `type`): voice clips, photos (a Messenger sticker is a photo with a
`sticker_id`, the thumbs-up included), a place (Messenger's older location
attachment), and everything else (video, files, shared posts and reels,
an `is_unsupported` message) as one the assistant asks to write about
instead. A story mention is not a file but what the message refers to.
The file is at `payload.url` on Meta's CDN.
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
    read_flag,
    read_identifier,
    read_number,
    read_object,
    read_objects,
    read_text,
)
from app.utilities.channels.meta_story_context import is_story_mention

MEDIA_KINDS: dict[str, AttachmentKind] = {
    "audio": AttachmentKind.AUDIO,
    "image": AttachmentKind.IMAGE,
}


def read_meta_attachments(message: JsonObject) -> list[InboundAttachment]:
    """
    The files of a message; a story mention is no file (the message's
    context note says what it is, `meta_story_context`).
    """

    attachments: list[InboundAttachment] = [
        read_attachment(item)
        for item in read_objects(message, "attachments")
        if not is_story_mention(item)
    ]
    if not attachments and read_flag(message, "is_unsupported"):
        return [build_unreadable_attachment(AttachmentKind.OTHER)]

    return attachments


def read_attachment(item: JsonObject) -> InboundAttachment:
    attachment_type: str | None = read_text(item, "type")
    payload: JsonObject = read_object(item, "payload") or {}
    if attachment_type == "image" and read_identifier(payload, "sticker_id"):
        return build_unreadable_attachment(AttachmentKind.STICKER)

    if attachment_type in MEDIA_KINDS:
        return build_media_attachment(
            MEDIA_KINDS[attachment_type], read_text(payload, "url")
        )

    if attachment_type == "location":
        coordinates: JsonObject = read_object(payload, "coordinates") or {}
        return build_location_attachment(
            read_number(coordinates, "lat"),
            read_number(coordinates, "long"),
            read_text(item, "title"),
        )

    return build_unreadable_attachment(AttachmentKind.OTHER)
