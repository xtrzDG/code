"""
The pages of an Ogg file, walked strictly from its first byte to its last.

A decoder that meets a page whose checksum fails skips it and searches the
bytes that follow for the next page, so a reader that trusted page sizes
alone could miss pages a decoder plays. Here every page must sit right
after the one before, carry a checksum that holds and belong to the one
logical stream that the first page begins; nothing may follow the page
that ends it.
"""

import struct
import zlib
from collections.abc import Iterator
from dataclasses import dataclass

CAPTURE_PATTERN: bytes = b"OggS"
HEADER_BYTES: int = 27
VERSION_AT: int = 4
FLAGS_AT: int = 5
GRANULE_AT: int = 6
CHECKSUM_AT: int = 22
SEGMENT_COUNT_AT: int = 26
CONTINUED_PACKET: int = 0x01
BEGINS_STREAM: int = 0x02
ENDS_STREAM: int = 0x04
# zlib computes the reflected CRC-32; Ogg's is the same polynomial unreflected.
BIT_REVERSED: bytes = bytes(int(f"{value:08b}"[::-1], 2) for value in range(256))
CHECKSUM_MASK: int = 0xFFFFFFFF


class OggStructureError(ValueError):
    """The bytes are not one well-formed Ogg stream."""


@dataclass(frozen=True)
class OggPage:
    """One page: its flags, granule position, segment sizes and body."""

    flags: int
    granule: int
    lacing: bytes
    body: bytes


def read_ogg_pages(content: bytes) -> Iterator[OggPage]:
    """
    Every page of the file in order.

    Raises:
        OggStructureError: a page is cut, broken or out of place, a second
            stream begins, or bytes follow the end of the stream.
    """

    position: int = 0
    serial: int | None = None
    has_ended: bool = False
    while position < len(content):
        if has_ended:
            raise OggStructureError("Bytes follow the end of the stream.")

        page, page_serial, position = read_page(content, position)
        begins: bool = bool(page.flags & BEGINS_STREAM)
        if serial is None and not begins:
            raise OggStructureError("The first page does not begin a stream.")

        if serial is not None and (begins or page_serial != serial):
            raise OggStructureError("More than one logical stream.")

        serial = page_serial
        has_ended = bool(page.flags & ENDS_STREAM)
        yield page


def read_page(content: bytes, start: int) -> tuple[OggPage, int, int]:
    """The page at `start`, its stream's serial number and where it ends."""

    header: bytes = content[start : start + HEADER_BYTES]
    if (
        len(header) < HEADER_BYTES
        or not header.startswith(CAPTURE_PATTERN)
        or header[VERSION_AT] != 0
    ):
        raise OggStructureError("Not an Ogg page.")

    lacing_end: int = start + HEADER_BYTES + header[SEGMENT_COUNT_AT]
    lacing: bytes = content[start + HEADER_BYTES : lacing_end]
    end: int = lacing_end + sum(lacing)
    if end > len(content):
        raise OggStructureError("A page is cut short.")

    page: bytearray = bytearray(content[start:end])
    (stored,) = struct.unpack_from("<I", page, CHECKSUM_AT)
    page[CHECKSUM_AT : CHECKSUM_AT + 4] = bytes(4)
    if ogg_checksum(bytes(page)) != stored:
        raise OggStructureError("A page's checksum does not hold.")

    granule, serial = struct.unpack_from("<qI", header, GRANULE_AT)
    return (
        OggPage(
            flags=header[FLAGS_AT],
            granule=granule,
            lacing=lacing,
            body=content[lacing_end:end],
        ),
        serial,
        end,
    )


def ogg_checksum(data: bytes) -> int:
    """
    The CRC-32 of an Ogg page (polynomial 0x04C11DB7, not reflected, no
    initial or final inversion), through zlib's reflected CRC-32 of the
    bit-reversed bytes.
    """

    reflected: int = zlib.crc32(data.translate(BIT_REVERSED), CHECKSUM_MASK)
    return int(f"{reflected ^ CHECKSUM_MASK:032b}"[::-1], 2)
