"""
How a customer message with attachments reads: for people (the readable
text that previews, language detection and the reply guard use) and for
the model (the same, with a line saying what each attachment was).

Lines for the model are English like every other platform line; they stay
inside the customer fence, so they speak for what the customer sent and
nothing else.
"""

from collections.abc import Sequence

from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import MessageAttachment, SharedLocation
from app.schemas.typings.media.strings import MapLinkUrl

MAP_LINK_TEMPLATE: str = "https://maps.google.com/?q={latitude},{longitude}"
VOICE_HEADER: str = "[Voice message, transcribed]"
VOICE_NOT_UNDERSTOOD: str = "[Voice message: no words could be made out]"
PHOTO_HEADER: str = "[Photo]"
PHOTO_NOT_OPENED: str = "[Photo: it could not be opened]"
LOCATION_HEADER: str = "[Location]"
UNREADABLE_LINES: dict[AttachmentKind, str] = {
    AttachmentKind.CONTACT: "[Contact card: it cannot be read]",
    AttachmentKind.STICKER: "[Sticker]",
    AttachmentKind.OTHER: "[File: it cannot be opened]",
}
COORDINATE_DIGITS: int = 6


def map_link(location: SharedLocation) -> MapLinkUrl:
    """A link that opens the place on a map in any browser or phone."""

    return MapLinkUrl(
        MAP_LINK_TEMPLATE.format(
            latitude=format_coordinate(float(location.latitude)),
            longitude=format_coordinate(float(location.longitude)),
        )
    )


def describe_location(location: SharedLocation) -> str:
    """'lat, lon', the place's name and address, and the map link."""

    coordinates: str = (
        f"{format_coordinate(float(location.latitude))}, "
        f"{format_coordinate(float(location.longitude))}"
    )
    labels: list[str] = [
        str(label)
        for label in (location.name, location.address)
        if label is not None and str(label).strip() != ""
    ]
    place: str = "" if not labels else f" ({', '.join(labels)})"
    return f"{coordinates}{place} {map_link(location)}"


def is_readable(attachment: MessageAttachment) -> bool:
    """The assistant can read it: words of a voice note, a photo, a place."""

    if attachment.problem is not None:
        return False

    if attachment.kind is AttachmentKind.AUDIO:
        return attachment.transcript is not None and bool(
            str(attachment.transcript).strip()
        )

    if attachment.kind is AttachmentKind.IMAGE:
        return attachment.storage_path is not None and attachment.media_type is not None

    return (
        attachment.kind is AttachmentKind.LOCATION and attachment.location is not None
    )


def has_readable_content(text: str, attachments: Sequence[MessageAttachment]) -> bool:
    """Something to answer: typed words or an attachment the assistant reads."""

    return text.strip() != "" or any(is_readable(item) for item in attachments)


def readable_message_text(text: str, attachments: Sequence[MessageAttachment]) -> str:
    """
    Everything the customer said, as words: the typed text and captions,
    the voice notes' transcripts and the places shared.
    """

    parts: list[str] = [text.strip()] if text.strip() else []
    for attachment in attachments:
        if attachment.kind is AttachmentKind.AUDIO and is_readable(attachment):
            parts.append(str(attachment.transcript).strip())
        elif attachment.location is not None and is_readable(attachment):
            parts.append(describe_location(attachment.location))

    return "\n\n".join(parts)


def describe_message_for_model(
    text: str, attachments: Sequence[MessageAttachment]
) -> str:
    """
    The message as the model reads it: one line per attachment (a voice
    note with its transcript, a photo shown next to the text, a place with
    its coordinates, or what could not be read), then the typed text.
    """

    parts: list[str] = [describe_attachment(item) for item in attachments]
    if text.strip():
        parts.append(text.strip())

    return "\n\n".join(parts)


def describe_attachment(attachment: MessageAttachment) -> str:
    if attachment.kind is AttachmentKind.AUDIO:
        if is_readable(attachment):
            return f"{VOICE_HEADER}\n{str(attachment.transcript).strip()}"

        return VOICE_NOT_UNDERSTOOD

    if attachment.kind is AttachmentKind.IMAGE:
        return PHOTO_HEADER if is_readable(attachment) else PHOTO_NOT_OPENED

    if attachment.kind is AttachmentKind.LOCATION and attachment.location is not None:
        return f"{LOCATION_HEADER} {describe_location(attachment.location)}"

    return UNREADABLE_LINES.get(attachment.kind, UNREADABLE_LINES[AttachmentKind.OTHER])


def format_coordinate(value: float) -> str:
    """At most six decimals (about 10 cm), without trailing zeros."""

    return f"{value:.{COORDINATE_DIGITS}f}".rstrip("0").rstrip(".")
