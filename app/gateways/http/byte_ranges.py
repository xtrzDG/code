"""
Byte-range requests (RFC 9110, section 14) for media served whole from memory.

Media players ask for parts of a file (`Range: bytes=0-1` first on Safari
and iOS, `bytes=0-` and later offsets to seek). Only one range per request
is served; several ranges, a malformed header or an `If-Range` (these
responses carry no validator to compare it with) get the whole body.
Offsets are technical values of the HTTP transport, not domain data.
"""

import re
from typing import NamedTuple

SINGLE_RANGE_PATTERN: re.Pattern[str] = re.compile(r"^bytes=(\d*)-(\d*)$")


class ByteRange(NamedTuple):
    """
    One requested range: `first_byte`-`last_byte` (both inclusive, the last
    one open when None), or the final `suffix_length` bytes.
    """

    first_byte: int | None
    last_byte: int | None
    suffix_length: int | None = None

    def starts_at_beginning(self) -> bool:
        """Whether the range starts at byte 0 (a player starting playback)."""

        return self.first_byte == 0


def read_byte_range(range_header: str | None, if_range: str | None) -> ByteRange | None:
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

        return ByteRange(first_byte=None, last_byte=None, suffix_length=int(last_text))

    first_byte = int(first_text)
    last_byte: int | None = None if last_text == "" else int(last_text)
    if last_byte is not None and last_byte < first_byte:
        return None

    return ByteRange(first_byte=first_byte, last_byte=last_byte)


def resolve_byte_range(
    requested: ByteRange,
    total_length: int,
) -> tuple[int, int] | None:
    """
    The first and last byte (inclusive) of the body to send; None when the
    range lies outside the body (answered with 416).
    """

    if requested.suffix_length is not None:
        if requested.suffix_length == 0 or total_length == 0:
            return None

        return max(0, total_length - requested.suffix_length), total_length - 1

    first_byte: int = requested.first_byte or 0
    if first_byte >= total_length:
        return None

    last_byte: int = (
        total_length - 1
        if requested.last_byte is None
        else min(requested.last_byte, total_length - 1)
    )
    return first_byte, last_byte
