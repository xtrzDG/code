"""
Byte-range requests (RFC 9110, section 14) of media served by the API.

Media players ask for parts of a file (`Range: bytes=0-1` first on Safari
and iOS, `bytes=0-` and later offsets to seek). Only one range per request
is served; several ranges, a malformed header or an `If-Range` (these
responses carry no validator to compare it with) get the whole body.
The header becomes a `RecordingByteRange` at this transport boundary; the
storage resolves it against the recording (`recording_byte_ranges`).
"""

import re

from app.schemas.dto.call_recordings import RecordingByteRange
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)

SINGLE_RANGE_PATTERN: re.Pattern[str] = re.compile(r"^bytes=(\d*)-(\d*)$")


def read_byte_range(
    range_header: str | None,
    if_range: str | None,
) -> RecordingByteRange | None:
    """The one range a request asks for; None to send the whole body."""

    if range_header is None or if_range is not None:
        return None

    match = SINGLE_RANGE_PATTERN.fullmatch(range_header.strip().lower())
    if match is None:
        return None

    first_text, last_text = match.groups()
    if first_text == "":
        if last_text == "":
            return None

        return RecordingByteRange(suffix_length=RecordingByteCount(int(last_text)))

    first_byte = int(first_text)
    last_byte: int | None = None if last_text == "" else int(last_text)
    if last_byte is not None and last_byte < first_byte:
        return None

    return RecordingByteRange(
        first_byte=RecordingByteOffset(first_byte),
        last_byte=None if last_byte is None else RecordingByteOffset(last_byte),
    )


def starts_at_beginning(byte_range: RecordingByteRange | None) -> bool:
    """Whether a read starts at byte 0 (a player starting a playback)."""

    return byte_range is None or (
        byte_range.first_byte is not None and int(byte_range.first_byte) == 0
    )
