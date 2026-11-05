"""Attachments of a webhook message as typed values, for every channel."""

from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import InboundAttachment, SharedLocation
from app.schemas.typings.media.constrained_floats import Latitude, Longitude
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
)
from app.schemas.typings.media.strings import (
    AttachmentCaption,
    LocationAddress,
    LocationName,
    ProviderMediaId,
    ProviderMediaType,
)

# Longer captions and place names are cut: no customer needs more.
MAX_CAPTION_LENGTH: int = 4000
MAX_PLACE_TEXT_LENGTH: int = 300
MAX_MEDIA_TYPE_LENGTH: int = 255
MAX_MEDIA_REFERENCE_LENGTH: int = 2048
NUL_CHARACTER: str = "\x00"


def build_media_attachment(
    kind: AttachmentKind,
    media_reference: str | None,
    mime_type: str | None = None,
    caption: str | None = None,
    declared_bytes: int | None = None,
    duration_seconds: int | None = None,
) -> InboundAttachment:
    """
    A file attachment; one whose reference is missing or absurdly long is
    kept without it (the customer still gets an answer, not silence).
    """

    is_reference_usable: bool = (
        media_reference is not None
        and 0 < len(media_reference) <= MAX_MEDIA_REFERENCE_LENGTH
    )
    return InboundAttachment(
        kind=kind,
        provider_media_id=(
            ProviderMediaId(media_reference)
            if media_reference is not None and is_reference_usable
            else None
        ),
        mime_type=(
            None
            if mime_type is None
            else ProviderMediaType(mime_type[:MAX_MEDIA_TYPE_LENGTH])
        ),
        caption=build_caption(caption),
        declared_bytes=(
            MediaByteCount(declared_bytes)
            if declared_bytes is not None and declared_bytes >= 0
            else None
        ),
        duration_seconds=(
            AudioDurationSeconds(duration_seconds)
            if duration_seconds is not None and duration_seconds >= 0
            else None
        ),
    )


def build_unreadable_attachment(
    kind: AttachmentKind, caption: str | None = None
) -> InboundAttachment:
    """A contact card, a sticker or another file the assistant does not read."""

    return InboundAttachment(kind=kind, caption=build_caption(caption))


def build_location_attachment(
    latitude: float | None,
    longitude: float | None,
    name: str | None = None,
    address: str | None = None,
) -> InboundAttachment:
    """A shared place; coordinates out of range make it an unreadable one."""

    location: SharedLocation | None = build_location(latitude, longitude, name, address)
    if location is None:
        return build_unreadable_attachment(AttachmentKind.OTHER)

    return InboundAttachment(kind=AttachmentKind.LOCATION, location=location)


def build_location(
    latitude: float | None,
    longitude: float | None,
    name: str | None,
    address: str | None,
) -> SharedLocation | None:
    if (
        latitude is None
        or longitude is None
        or not -90.0 <= latitude <= 90.0
        or not -180.0 <= longitude <= 180.0
    ):
        return None

    return SharedLocation(
        latitude=Latitude(float(latitude)),
        longitude=Longitude(float(longitude)),
        name=None if not name else LocationName(clean_place_text(name)),
        address=None if not address else LocationAddress(clean_place_text(address)),
    )


def build_caption(caption: str | None) -> AttachmentCaption | None:
    """The caption without NUL characters (Postgres JSONB refuses them)."""

    cleaned: str = "" if caption is None else caption.replace(NUL_CHARACTER, "")
    if cleaned.strip() == "":
        return None

    return AttachmentCaption(cleaned[:MAX_CAPTION_LENGTH])


def has_content(text: str, attachments: list[InboundAttachment]) -> bool:
    """A message worth an answer: words or at least one attachment."""

    return text.strip() != "" or bool(attachments)


def clean_place_text(text: str) -> str:
    return text.replace(NUL_CHARACTER, "")[:MAX_PLACE_TEXT_LENGTH]
