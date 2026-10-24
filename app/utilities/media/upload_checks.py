"""
What a file a website visitor uploads must be before it is kept.

The chat takes photos (JPEG, PNG, WebP) and voice notes as browsers record
them (WebM or Ogg with Opus, MP4 with AAC from Safari or Opus). The type
the browser declares must be one of them and the file's own bytes must say
the same; a voice note's length is measured from its audio as well as its
container's claims (only audio tracks: a video is not a voice note) and a
photo leaves without its metadata.
"""

from collections.abc import Callable

from app.schemas.constants.media import AttachmentKind
from app.schemas.typings.media.constrained_strings import (
    DeclaredMediaType,
    MessageMediaType,
)
from app.schemas.typings.media.strings import DeclaredUploadType
from app.utilities.media.jpeg_metadata import strip_jpeg_metadata
from app.utilities.media.png_metadata import strip_png_metadata
from app.utilities.media.voice_note_length import VOICE_NOTE_READERS
from app.utilities.media.webp_metadata import strip_webp_metadata

IMAGE_STRIPPERS: dict[MessageMediaType, Callable[[bytes], bytes]] = {
    MessageMediaType("image/jpeg"): strip_jpeg_metadata,
    MessageMediaType("image/png"): strip_png_metadata,
    MessageMediaType("image/webp"): strip_webp_metadata,
}
UPLOAD_IMAGE_TYPES: tuple[MessageMediaType, ...] = tuple(IMAGE_STRIPPERS)
UPLOAD_AUDIO_TYPES: tuple[MessageMediaType, ...] = tuple(VOICE_NOTE_READERS)
UPLOAD_KINDS: dict[MessageMediaType, AttachmentKind] = {
    **dict.fromkeys(UPLOAD_IMAGE_TYPES, AttachmentKind.IMAGE),
    **dict.fromkeys(UPLOAD_AUDIO_TYPES, AttachmentKind.AUDIO),
}


def read_declared_type(declared: DeclaredUploadType | None) -> DeclaredMediaType | None:
    """
    The media type a browser declared, without parameters, lower case;
    None when it declared none or something that is not a media type.
    """

    if declared is None:
        return None

    base: str = str(declared).split(";", 1)[0].strip().lower()
    try:
        return DeclaredMediaType(base)
    except ValueError:
        return None


def accepted_upload_type(declared: DeclaredMediaType | None) -> MessageMediaType | None:
    """The chat's own type that the declared one names; None for any other."""

    if declared is None:
        return None

    named: str = str(declared)
    return next((kind for kind in UPLOAD_KINDS if str(kind) == named), None)


def strip_image_metadata(content: bytes, media_type: MessageMediaType) -> bytes:
    """
    The photo without its metadata (`*_metadata` modules).

    Raises:
        MalformedMediaFileError: its structure does not add up.
    """

    return IMAGE_STRIPPERS[media_type](content)
