"""
What a downloaded file really is, read from its first bytes.

The type a platform declares is never trusted: a stored file is served
back to the cabinet with the type found here, so a file that is not audio
or a picture the model reads (an HTML page, an SVG, a PDF) is refused
instead of stored.
"""

from app.schemas.constants.media import AttachmentKind
from app.schemas.typings.media.constrained_strings import MessageMediaType

MP3_FRAME_SYNC_MASK: int = 0xE0
HEADER_BYTES_NEEDED: int = 12


def sniff_media_type(content: bytes) -> MessageMediaType | None:
    """The audio or image type of the file's bytes; None for anything else."""

    if len(content) < HEADER_BYTES_NEEDED:
        return None

    head: bytes = content[:HEADER_BYTES_NEEDED]
    detected: str | None = sniff_image(head) or sniff_audio(head)
    return None if detected is None else MessageMediaType(detected)


def sniff_image(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"

    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"

    return None


def sniff_audio(head: bytes) -> str | None:
    if head.startswith(b"OggS"):
        return "audio/ogg"

    if head.startswith(b"ID3") or (
        head[0] == 0xFF and head[1] & MP3_FRAME_SYNC_MASK == MP3_FRAME_SYNC_MASK
    ):
        return "audio/mpeg"

    if head[4:8] == b"ftyp":
        return "audio/mp4"

    if head.startswith(b"#!AMR"):
        return "audio/amr"

    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return "audio/wav"

    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"

    return None


def kind_of_media_type(media_type: MessageMediaType) -> AttachmentKind:
    """AUDIO or IMAGE, as the media type says."""

    return (
        AttachmentKind.IMAGE
        if str(media_type).startswith("image/")
        else AttachmentKind.AUDIO
    )
