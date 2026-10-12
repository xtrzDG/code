"""
What a file a website visitor uploads must be before it is kept.

The chat takes photos (JPEG, PNG, WebP) and voice notes as browsers record
them (WebM or Ogg with Opus, MP4 with AAC from Safari). The type the browser
declares must be one of them and the file's own bytes must say the same;
a voice note's length is read from its container (only audio tracks: a
video is not a voice note) and a photo leaves without its metadata.
"""

from collections.abc import Callable

from app.schemas.constants.media import AttachmentKind
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.strings import DeclaredUploadType
from app.utilities.media.audio_duration import read_audio_duration_seconds
from app.utilities.media.jpeg_metadata import strip_jpeg_metadata
from app.utilities.media.png_metadata import strip_png_metadata
from app.utilities.media.webm_audio import read_webm_audio_seconds
from app.utilities.media.webp_metadata import strip_webp_metadata

IMAGE_STRIPPERS: dict[str, Callable[[bytes], bytes]] = {
    "image/jpeg": strip_jpeg_metadata,
    "image/png": strip_png_metadata,
    "image/webp": strip_webp_metadata,
}
UPLOAD_IMAGE_TYPES: tuple[str, ...] = tuple(IMAGE_STRIPPERS)
UPLOAD_AUDIO_TYPES: tuple[str, ...] = ("audio/webm", "audio/ogg", "audio/mp4")
UPLOAD_KINDS: dict[str, AttachmentKind] = {
    **dict.fromkeys(UPLOAD_IMAGE_TYPES, AttachmentKind.IMAGE),
    **dict.fromkeys(UPLOAD_AUDIO_TYPES, AttachmentKind.AUDIO),
}
OGG_VIDEO_HEADERS: tuple[bytes, ...] = (b"\x80theora", b"OVP80", b"\x80daala")
MP4_HANDLER_TAG: bytes = b"hdlr"
# 'hdlr' box: version and flags (4), pre_defined (4), then the handler type.
MP4_HANDLER_TYPE_OFFSET: int = 12
MP4_VIDEO_HANDLER: bytes = b"vide"
MP4_SOUND_HANDLER: bytes = b"soun"
OGG_HEAD_BYTES: int = 64 * 1024


def read_declared_type(declared: DeclaredUploadType | None) -> str | None:
    """The media type a browser declared, without parameters, lower case."""

    if declared is None:
        return None

    base: str = str(declared).split(";", 1)[0].strip().lower()
    return base or None


def upload_kind_of(media_type: str | None) -> AttachmentKind | None:
    """IMAGE or AUDIO for a type the chat takes; None for any other."""

    return None if media_type is None else UPLOAD_KINDS.get(media_type)


def strip_image_metadata(content: bytes, media_type: MessageMediaType) -> bytes:
    """
    The photo without its metadata (`*_metadata` modules).

    Raises:
        MalformedMediaFileError: its structure does not add up.
    """

    return IMAGE_STRIPPERS[str(media_type)](content)


def measure_voice_note(content: bytes, media_type: MessageMediaType) -> int | None:
    """
    Whole seconds of a recording with only audio in it; None when it holds
    video, or its container does not tell its length.
    """

    kind: str = str(media_type)
    if kind == "audio/webm":
        return read_webm_audio_seconds(content)

    if kind == "audio/ogg" and has_ogg_video(content):
        return None

    if kind == "audio/mp4" and not is_mp4_sound_only(content):
        return None

    return read_audio_duration_seconds(content)


def has_ogg_video(content: bytes) -> bool:
    head: bytes = content[:OGG_HEAD_BYTES]
    return any(header in head for header in OGG_VIDEO_HEADERS)


def is_mp4_sound_only(content: bytes) -> bool:
    """At least one sound track and no video track (the 'hdlr' boxes)."""

    handlers: set[bytes] = set()
    found: int = content.find(MP4_HANDLER_TAG)
    while found >= 0:
        handler_at: int = found + MP4_HANDLER_TYPE_OFFSET
        handlers.add(content[handler_at : handler_at + 4])
        found = content.find(MP4_HANDLER_TAG, found + 1)

    return MP4_SOUND_HANDLER in handlers and MP4_VIDEO_HANDLER not in handlers
