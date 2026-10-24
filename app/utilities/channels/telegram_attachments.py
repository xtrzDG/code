"""
Attachments of a Telegram Bot API message: a voice note or audio file, a
photo (the largest size within the download limit), a picture sent as a
file, a place or venue, a contact card of someone else (the sender's own
number is read as their phone instead), a sticker, and everything else
(video, video notes, animations, documents, polls, dice) as one the
assistant asks to write about instead. The caption is the attachment's.
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
    read_objects,
    read_text,
)

# The Bot API hands out files of at most 20 MB (getFile).
TELEGRAM_DOWNLOAD_LIMIT_BYTES: int = 20 * 1024 * 1024
UNREADABLE_FIELDS: tuple[tuple[str, AttachmentKind], ...] = (
    ("sticker", AttachmentKind.STICKER),
    ("video", AttachmentKind.OTHER),
    ("video_note", AttachmentKind.OTHER),
    ("animation", AttachmentKind.OTHER),
    ("document", AttachmentKind.OTHER),
    ("poll", AttachmentKind.OTHER),
    ("dice", AttachmentKind.OTHER),
    ("story", AttachmentKind.OTHER),
)


def read_telegram_attachments(
    message: JsonObject, is_own_contact: bool
) -> list[InboundAttachment]:
    """
    The message's attachment (Telegram sends one per message); a contact
    the customer shares about themselves is not one.
    """

    caption: str | None = read_text(message, "caption")
    for field in ("voice", "audio"):
        audio: JsonObject | None = read_object(message, field)
        if audio is not None:
            return [read_file(audio, AttachmentKind.AUDIO, caption)]

    photo: JsonObject | None = pick_photo_size(read_objects(message, "photo"))
    if photo is not None:
        return [read_file(photo, AttachmentKind.IMAGE, caption)]

    document: JsonObject | None = read_object(message, "document")
    if document is not None and (read_text(document, "mime_type") or "").startswith(
        "image/"
    ):
        return [read_file(document, AttachmentKind.IMAGE, caption)]

    place: JsonObject | None = read_place(message)
    if place is not None:
        return [place_attachment(message, place)]

    if read_object(message, "contact") is not None:
        return (
            []
            if is_own_contact
            else [build_unreadable_attachment(AttachmentKind.CONTACT)]
        )

    for field, kind in UNREADABLE_FIELDS:
        if read_object(message, field) is not None:
            return [build_unreadable_attachment(kind, caption)]

    return []


def read_file(
    file: JsonObject, kind: AttachmentKind, caption: str | None
) -> InboundAttachment:
    return build_media_attachment(
        kind,
        read_identifier(file, "file_id"),
        read_text(file, "mime_type"),
        caption,
        read_integer(file, "file_size"),
        read_integer(file, "duration"),
    )


def pick_photo_size(sizes: list[JsonObject]) -> JsonObject | None:
    """The largest size Telegram hands out (sizes come smallest first)."""

    allowed: list[JsonObject] = [
        size
        for size in sizes
        if (read_integer(size, "file_size") or 0) <= TELEGRAM_DOWNLOAD_LIMIT_BYTES
    ]
    return allowed[-1] if allowed else (sizes[0] if sizes else None)


def read_place(message: JsonObject) -> JsonObject | None:
    venue: JsonObject | None = read_object(message, "venue")
    if venue is not None:
        return read_object(venue, "location")

    return read_object(message, "location")


def place_attachment(message: JsonObject, place: JsonObject) -> InboundAttachment:
    venue: JsonObject = read_object(message, "venue") or {}
    return build_location_attachment(
        read_number(place, "latitude"),
        read_number(place, "longitude"),
        read_text(venue, "title"),
        read_text(venue, "address"),
    )
