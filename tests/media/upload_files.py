"""
Small, structurally real files of the kinds a website visitor uploads,
built byte by byte: JPEG, PNG and WebP photos carrying metadata, WebM, Ogg
and MP4 recordings with audio or video tracks.
"""

import struct
import zlib

# --- WebM (EBML) -----------------------------------------------------------

UNKNOWN_SIZE: bytes = b"\x01\xff\xff\xff\xff\xff\xff\xff"
AUDIO_TRACK: int = 2
VIDEO_TRACK: int = 1
MILLISECONDS_PER_SECOND: int = 1000
# A cluster's blocks sit at most 32.767 s after its timecode (int16 offset).
CLUSTER_SECONDS: int = 10


def ebml(element_id: int, data: bytes) -> bytes:
    """An element with its data size as an 8-byte variable-length integer."""

    id_bytes: bytes = element_id.to_bytes((element_id.bit_length() + 7) // 8, "big")
    return id_bytes + (0x01 << 56 | len(data)).to_bytes(8, "big") + data


def uint(value: int, size: int = 4) -> bytes:
    return value.to_bytes(size, "big")


def simple_block(offset_ms: int) -> bytes:
    """Track 1, `offset_ms` after its cluster, a keyframe, a few bytes."""

    return ebml(0xA3, b"\x81" + struct.pack(">h", offset_ms) + b"\x80" + bytes(8))


def webm_recording(
    seconds: int,
    track_types: tuple[int, ...] = (AUDIO_TRACK,),
    header_duration: bool = False,
    doc_type: bytes = b"webm",
) -> bytes:
    """
    A WebM file as MediaRecorder writes it: an unknown-size segment and
    clusters, no duration in the header unless asked, blocks to `seconds`.
    """

    header: bytes = ebml(0x1A45DFA3, ebml(0x4282, doc_type))
    info_fields: bytes = ebml(0x2AD7B1, uint(1_000_000, 3))
    if header_duration:
        info_fields += ebml(0x4489, struct.pack(">d", seconds * 1000.0))
    tracks: bytes = ebml(
        0x1654AE6B,
        b"".join(ebml(0xAE, ebml(0x83, uint(kind, 1))) for kind in track_types),
    )
    clusters: bytes = b""
    last_ms: int = seconds * MILLISECONDS_PER_SECOND
    for start in range(0, max(seconds, 1), CLUSTER_SECONDS):
        start_ms: int = start * MILLISECONDS_PER_SECOND
        end_ms: int = min(last_ms, start_ms + CLUSTER_SECONDS * 1000 - 20)
        clusters += (
            uint(0x1F43B675)
            + UNKNOWN_SIZE
            + ebml(0xE7, uint(start_ms))
            + simple_block(0)
            + simple_block(end_ms - start_ms)
        )
    return (
        header
        + uint(0x18538067)
        + UNKNOWN_SIZE
        + ebml(0x1549A966, info_fields)
        + tracks
        + clusters
    )


# --- Ogg and MP4 -------------------------------------------------------------


def ogg_theora_bytes() -> bytes:
    """An Ogg stream whose first packet is a Theora video header."""

    return b"OggS" + bytes(24) + b"\x80theora" + bytes(64)


def mp4_box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def mp4_recording(seconds: int, handlers: tuple[bytes, ...] = (b"soun",)) -> bytes:
    """An M4A as Safari records it: a movie header and one track per handler."""

    movie_header: bytes = mp4_box(
        b"mvhd", bytes(4) + bytes(8) + struct.pack(">II", 1000, seconds * 1000)
    )
    tracks: bytes = b"".join(
        mp4_box(
            b"trak",
            mp4_box(b"mdia", mp4_box(b"hdlr", bytes(8) + handler + bytes(12))),
        )
        for handler in handlers
    )
    return mp4_box(b"ftyp", b"M4A " + bytes(4)) + mp4_box(
        b"moov", movie_header + tracks
    )


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
