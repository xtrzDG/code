"""
Byte ranges of recordings (RFC 9110, section 14): which part of a recording
a requested range names, and that part cut out of a whole recording.
Offsets are inclusive, as in `Range: bytes=first-last`.
"""

from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingPart,
)
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)


def resolve_byte_span(
    wanted: RecordingByteRange,
    total_length: int,
) -> tuple[int, int] | None:
    """
    The first and last byte (inclusive) of the part to send; None when the
    range lies outside a recording of `total_length` bytes (HTTP 416).
    """

    if wanted.suffix_length is not None:
        if int(wanted.suffix_length) == 0 or total_length == 0:
            return None

        return max(0, total_length - int(wanted.suffix_length)), total_length - 1

    first_byte: int = 0 if wanted.first_byte is None else int(wanted.first_byte)
    if first_byte >= total_length:
        return None

    last_byte: int = (
        total_length - 1
        if wanted.last_byte is None
        else min(int(wanted.last_byte), total_length - 1)
    )
    return first_byte, last_byte


def cut_recording_part(
    audio: RecordingAudio,
    wanted: RecordingByteRange | None,
) -> RecordingPart:
    """The part of a whole recording a read asked for (all of it without a range)."""

    total_length: int = len(audio.content)
    span: tuple[int, int] | None = (
        (0, total_length - 1)
        if wanted is None
        else resolve_byte_span(wanted, total_length)
    )
    if span is None:
        return outside_the_recording(audio, total_length)

    first_byte, last_byte = span
    return RecordingPart(
        content=audio.content[first_byte : last_byte + 1],
        media_type=audio.media_type,
        first_byte=RecordingByteOffset(first_byte),
        total_bytes=RecordingByteCount(total_length),
    )


def outside_the_recording(audio: RecordingAudio, total_length: int) -> RecordingPart:
    """The empty part of a range that lies outside the recording."""

    return RecordingPart(
        content=b"",
        media_type=audio.media_type,
        first_byte=RecordingByteOffset(total_length),
        total_bytes=RecordingByteCount(total_length),
    )
