"""
A JPEG photo without its metadata, rebuilt from its own segments.

Kept: what decoding needs (quantization and Huffman tables, the frame and
scan headers, restart intervals, the compressed scans), the JFIF header
without its thumbnail, the colour profile (ICC) and Adobe's colour
transform, and the orientation (`exif_orientation`). Dropped: Exif and XMP
(place, time, device, thumbnails), IPTC and Photoshop blocks, comments,
the other application segments, and whatever follows the end of the image
(phones append preview, depth and gain-map pictures there, each with Exif
of its own). The pixels are never decoded, so a hostile file cannot reach
an image decoder here; a file whose segments do not add up is refused.
"""

from app.schemas.exceptions.media_errors import MalformedMediaFileError
from app.utilities.media.exif_orientation import (
    orientation_only_exif,
    read_exif_orientation,
)

START_OF_IMAGE: bytes = b"\xff\xd8"
END_OF_IMAGE: int = 0xD9
START_OF_SCAN: int = 0xDA
APP0: int = 0xE0
APP1: int = 0xE1
APP2: int = 0xE2
APP14: int = 0xEE
MARKER_PREFIX: int = 0xFF
STUFFED_BYTE: int = 0x00
RESTART_MARKERS: range = range(0xD0, 0xD8)
STANDALONE_MARKERS: frozenset[int] = frozenset({0x01, *RESTART_MARKERS})
# Frame headers, Huffman and arithmetic tables (C0-CF), the scan, number of
# lines, quantization tables, restart interval, hierarchical frames (DA-DF).
DECODING_MARKERS: frozenset[int] = frozenset({*range(0xC0, 0xD0), *range(0xDA, 0xE0)})
JFIF_IDENTIFIER: bytes = b"JFIF\x00"
# Identifier, version, units, densities: the JFIF header up to its thumbnail.
JFIF_HEADER_LENGTH: int = 12
ICC_IDENTIFIER: bytes = b"ICC_PROFILE\x00"
ADOBE_IDENTIFIER: bytes = b"Adobe"
LENGTH_BYTES: int = 2


def strip_jpeg_metadata(content: bytes) -> bytes:
    """
    The photo with only its decoding segments, colour data and orientation.

    Raises:
        MalformedMediaFileError: no start or end of image, a segment that runs
            past the end, or a marker where image data was expected.
    """

    if not content.startswith(START_OF_IMAGE):
        raise MalformedMediaFileError(
            "A JPEG file starts with its start-of-image marker."
        )

    kept = bytearray(START_OF_IMAGE)
    exif_position: int = len(kept)
    orientation: int | None = None
    position: int = len(START_OF_IMAGE)
    while True:
        marker, position = read_marker(content, position)
        if marker == END_OF_IMAGE:
            kept += bytes((MARKER_PREFIX, END_OF_IMAGE))
            break

        if marker in STANDALONE_MARKERS:
            kept += bytes((MARKER_PREFIX, marker))
            continue

        payload, position = read_segment(content, position)
        if marker == APP1 and orientation is None:
            orientation = read_exif_orientation(payload)
        kept_payload: bytes | None = keep_payload(marker, payload)
        if kept_payload is not None:
            kept += segment_bytes(marker, kept_payload)
            if marker == APP0 and exif_position == len(START_OF_IMAGE):
                exif_position = len(kept)

        if marker == START_OF_SCAN:
            scan_end: int = find_scan_end(content, position)
            kept += content[position:scan_end]
            position = scan_end

    if orientation is not None:
        kept[exif_position:exif_position] = segment_bytes(
            APP1, orientation_only_exif(orientation)
        )
    return bytes(kept)


def read_marker(content: bytes, position: int) -> tuple[int, int]:
    """The next marker (fill bytes skipped) and the position after it."""

    if position >= len(content) or content[position] != MARKER_PREFIX:
        raise MalformedMediaFileError("A JPEG segment must start with a marker.")

    while position < len(content) and content[position] == MARKER_PREFIX:
        position += 1
    if position >= len(content):
        raise MalformedMediaFileError(
            "The JPEG file ends before its end-of-image marker."
        )

    return content[position], position + 1


def read_segment(content: bytes, position: int) -> tuple[bytes, int]:
    """A segment's payload (after its length) and the position after it."""

    if position + LENGTH_BYTES > len(content):
        raise MalformedMediaFileError("A JPEG segment is cut off.")

    length: int = int.from_bytes(content[position : position + LENGTH_BYTES], "big")
    end: int = position + length
    if length < LENGTH_BYTES or end > len(content):
        raise MalformedMediaFileError("A JPEG segment runs past the end of the file.")

    return content[position + LENGTH_BYTES : end], end


def keep_payload(marker: int, payload: bytes) -> bytes | None:
    """What of a segment stays (None: dropped)."""

    if marker in DECODING_MARKERS:
        return payload

    if marker == APP0 and payload.startswith(JFIF_IDENTIFIER):
        if len(payload) < JFIF_HEADER_LENGTH:
            raise MalformedMediaFileError("The JFIF header is cut off.")
        # The same header without its thumbnail (0 x 0 pixels).
        return payload[:JFIF_HEADER_LENGTH] + b"\x00\x00"

    if marker == APP2 and payload.startswith(ICC_IDENTIFIER):
        return payload

    if marker == APP14 and payload.startswith(ADOBE_IDENTIFIER):
        return payload

    return None


def find_scan_end(content: bytes, position: int) -> int:
    """
    Where a scan's compressed data ends: at the first marker that is not a
    stuffed 0xFF byte or a restart marker inside the data.
    """

    while True:
        found: int = content.find(MARKER_PREFIX, position)
        if found < 0 or found + 1 >= len(content):
            raise MalformedMediaFileError("The JPEG file ends inside its image data.")

        following: int = content[found + 1]
        if following == STUFFED_BYTE or following in RESTART_MARKERS:
            position = found + 2
        elif following == MARKER_PREFIX:
            position = found + 1
        else:
            return found


def segment_bytes(marker: int, payload: bytes) -> bytes:
    length: int = len(payload) + LENGTH_BYTES
    if length > 0xFFFF:
        raise MalformedMediaFileError("A JPEG segment is longer than a segment can be.")

    return bytes((MARKER_PREFIX, marker)) + length.to_bytes(2, "big") + payload
