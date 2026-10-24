"""
Small, structurally real photos of the kinds a website visitor uploads,
built byte by byte: JPEG, PNG and WebP carrying metadata (the recordings
are in `recording_files` and `mp4_files`).
"""

import struct
import zlib

# --- JPEG ------------------------------------------------------------------

GPS_TEXT: bytes = b"GPS 41.7151N 44.8271E"
DEVICE_TEXT: bytes = b"PhoneMaker X12 serial 0000"
COMMENT_TEXT: bytes = b"taken at home"


def jpeg_segment(marker: int, payload: bytes) -> bytes:
    return bytes((0xFF, marker)) + struct.pack(">H", len(payload) + 2) + payload


def exif_payload(orientation: int | None) -> bytes:
    """Little-endian Exif: Orientation (when given), a maker text, GPS bytes."""

    entries: list[bytes] = []
    if orientation is not None:
        entries.append(struct.pack("<HHIHH", 0x0112, 3, 1, orientation, 0))
    maker_at: int = 8 + 2 + 12 * (len(entries) + 1) + 4
    entries.append(struct.pack("<HHII", 0x010F, 2, len(DEVICE_TEXT), maker_at))
    tiff: bytes = (
        b"II"
        + struct.pack("<HI", 42, 8)
        + struct.pack("<H", len(entries))
        + b"".join(entries)
        + struct.pack("<I", 0)
        + DEVICE_TEXT
        + GPS_TEXT
    )
    return b"Exif\x00\x00" + tiff


def jpeg_photo(orientation: int | None = 6, trailer: bytes = b"") -> bytes:
    """A one-pixel baseline JPEG with JFIF, Exif, XMP, a comment and tables."""

    jfif: bytes = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    xmp: bytes = b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta>" + GPS_TEXT
    quantization: bytes = b"\x00" + bytes(range(1, 65))
    frame: bytes = b"\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    huffman: bytes = b"\x00" + bytes(16) + b""
    scan_header: bytes = b"\x01\x01\x00\x00\x3f\x00"
    scan_data: bytes = b"\x12\x34\xff\x00\x56\xff\xd0\x78"
    return (
        b"\xff\xd8"
        + jpeg_segment(0xE0, jfif)
        + jpeg_segment(0xE1, exif_payload(orientation))
        + jpeg_segment(0xE1, xmp)
        + jpeg_segment(0xFE, COMMENT_TEXT)
        + jpeg_segment(0xDB, quantization)
        + jpeg_segment(0xC0, frame)
        + jpeg_segment(0xC4, huffman)
        + jpeg_segment(0xDA, scan_header)
        + scan_data
        + b"\xff\xd9"
        + trailer
    )


# --- PNG and WebP ------------------------------------------------------------


def png_chunk(kind: bytes, data: bytes) -> bytes:
    crc: int = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def png_photo() -> bytes:
    """A 1x1 PNG with text, Exif and time chunks beside the image."""

    header: bytes = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels: bytes = zlib.compress(b"\x00\xff\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"tEXt", b"Comment\x00" + COMMENT_TEXT)
        + png_chunk(b"eXIf", exif_payload(None)[6:])
        + png_chunk(b"tIME", bytes(7))
        + png_chunk(b"IDAT", pixels)
        + png_chunk(b"IEND", b"")
    )


def riff_chunk(kind: bytes, data: bytes) -> bytes:
    return kind + struct.pack("<I", len(data)) + data + (b"\x00" * (len(data) % 2))


def webp_photo() -> bytes:
    """An extended WebP: a lossless frame with Exif and XMP chunks and flags."""

    flags: int = 0x08 | 0x04
    header: bytes = bytes((flags, 0, 0, 0)) + bytes(6)
    body: bytes = (
        b"WEBP"
        + riff_chunk(b"VP8X", header)
        + riff_chunk(b"VP8L", b"\x2f" + bytes(12))
        + riff_chunk(b"EXIF", exif_payload(None)[6:])
        + riff_chunk(b"XMP ", b"<x:xmpmeta>" + GPS_TEXT)
    )
    return b"RIFF" + struct.pack("<I", len(body)) + body
