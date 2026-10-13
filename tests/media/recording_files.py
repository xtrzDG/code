"""
Small, structurally real voice recordings built byte by byte: WebM as
MediaRecorder writes it and Ogg Opus with real page checksums, honest or
with forged lengths (header durations, block times, granule positions).
"""

import struct

# --- Opus packets ----------------------------------------------------------

# Configuration 31 (CELT, 20 ms frames), mono: one frame, or a count byte.
OPUS_20_MS: bytes = b"\xf8\x11\x22"
OPUS_60_MS: bytes = b"\xfb\x03\x11\x22"
PACKETS_PER_SECOND_20_MS: int = 50

# --- WebM (EBML) -----------------------------------------------------------

UNKNOWN_SIZE: bytes = b"\x01\xff\xff\xff\xff\xff\xff\xff"
AUDIO_TRACK: int = 2
VIDEO_TRACK: int = 1
OPUS_CODEC: bytes = b"A_OPUS"
CODECS: dict[int, bytes] = {AUDIO_TRACK: OPUS_CODEC, VIDEO_TRACK: b"V_VP8"}
MILLISECONDS_PER_SECOND: int = 1000
# A cluster's blocks sit at most 32.767 s after its timecode (int16 offset).
CLUSTER_SECONDS: int = 10
KEYFRAME: int = 0x80


def ebml(element_id: int, data: bytes) -> bytes:
    """An element with its data size as an 8-byte variable-length integer."""

    id_bytes: bytes = element_id.to_bytes((element_id.bit_length() + 7) // 8, "big")
    return id_bytes + (0x01 << 56 | len(data)).to_bytes(8, "big") + data


def uint(value: int, size: int = 4) -> bytes:
    return value.to_bytes(size, "big")


def simple_block(
    offset_ms: int, packet: bytes = OPUS_20_MS, flags: int = KEYFRAME
) -> bytes:
    """Track 1, `offset_ms` after its cluster, one Opus packet."""

    return ebml(0xA3, b"\x81" + struct.pack(">h", offset_ms) + bytes((flags,)) + packet)


def webm_header(
    track_types: tuple[int, ...] = (AUDIO_TRACK,),
    duration_ms: float | None = None,
    doc_type: bytes = b"webm",
    track_extra: bytes = b"",
) -> bytes:
    """The EBML header, an unknown-size segment, its info and tracks."""

    info_fields: bytes = ebml(0x2AD7B1, uint(1_000_000, 3))
    if duration_ms is not None:
        info_fields += ebml(0x4489, struct.pack(">d", duration_ms))
    tracks: bytes = ebml(
        0x1654AE6B,
        b"".join(
            ebml(
                0xAE, ebml(0x83, uint(kind, 1)) + ebml(0x86, CODECS[kind]) + track_extra
            )
            for kind in track_types
        ),
    )
    return (
        ebml(0x1A45DFA3, ebml(0x4282, doc_type))
        + uint(0x18538067)
        + UNKNOWN_SIZE
        + ebml(0x1549A966, info_fields)
        + tracks
    )


def cluster(timecode_ms: int, blocks: bytes) -> bytes:
    return uint(0x1F43B675) + UNKNOWN_SIZE + ebml(0xE7, uint(timecode_ms)) + blocks


def webm_recording(
    seconds: int,
    track_types: tuple[int, ...] = (AUDIO_TRACK,),
    header_duration: bool = False,
    doc_type: bytes = b"webm",
) -> bytes:
    """
    A sparse WebM file as MediaRecorder writes it: an unknown-size segment
    and clusters, no duration in the header unless asked, a block at the
    start and the end of each cluster, the last one `seconds` in.
    """

    clusters: bytes = b""
    last_ms: int = seconds * MILLISECONDS_PER_SECOND
    for start in range(0, max(seconds, 1), CLUSTER_SECONDS):
        start_ms: int = start * MILLISECONDS_PER_SECOND
        end_ms: int = min(last_ms, start_ms + CLUSTER_SECONDS * 1000 - 20)
        clusters += cluster(start_ms, simple_block(0) + simple_block(end_ms - start_ms))
    duration_ms: float | None = last_ms * 1.0 if header_duration else None
    return webm_header(track_types, duration_ms, doc_type) + clusters


def webm_opus_stream(
    packets: int,
    packet: bytes = OPUS_60_MS,
    spacing_ms: int = 60,
    duration_ms: float | None = None,
) -> bytes:
    """
    A dense WebM recording: `packets` Opus packets, one block each,
    `spacing_ms` apart on the clock (a forger may squeeze them together).
    """

    blocks_per_cluster: int = (
        packets if spacing_ms == 0 else (CLUSTER_SECONDS * 1000) // spacing_ms
    )
    clusters: bytes = b""
    for first in range(0, packets, blocks_per_cluster):
        count: int = min(blocks_per_cluster, packets - first)
        blocks: bytes = b"".join(
            simple_block(index * spacing_ms, packet) for index in range(count)
        )
        clusters += cluster(first * spacing_ms, blocks)
    return webm_header(duration_ms=duration_ms) + clusters


# A Void element (0xEC) claiming some 2 GB: it runs past the end of any
# voice note, and a decoder resyncs at the next cluster after it.
OVERSIZED_VOID: bytes = bytes.fromhex("EC010000007FFFFFFF")


def with_element_before_second_cluster(recording: bytes, element: bytes) -> bytes:
    """`recording` with `element` put in front of its second cluster."""

    cluster_id: bytes = uint(0x1F43B675)
    second: int = recording.index(cluster_id, recording.index(cluster_id) + 1)
    return recording[:second] + element + recording[second:]


# --- Ogg Opus ----------------------------------------------------------------

OGG_SERIAL: int = 0x5EED
PRE_SKIP: int = 312
OPUS_HEAD: bytes = (
    b"OpusHead" + bytes((1, 1)) + struct.pack("<HIhB", PRE_SKIP, 48_000, 0, 0)
)
OPUS_TAGS: bytes = b"OpusTags" + struct.pack("<I", 4) + b"test" + struct.pack("<I", 0)
BEGINS: int = 0x02
ENDS: int = 0x04


def crc_table() -> list[int]:
    table: list[int] = []
    for byte in range(256):
        value: int = byte << 24
        for _ in range(8):
            value = ((value << 1) ^ 0x04C11DB7) if value & 0x80000000 else value << 1
        table.append(value & 0xFFFFFFFF)
    return table


CRC_TABLE: list[int] = crc_table()


def ogg_crc(data: bytes) -> int:
    """Ogg's CRC-32, computed the plain way (a check on the reader's zlib one)."""

    value: int = 0
    for byte in data:
        value = ((value << 8) & 0xFFFFFFFF) ^ CRC_TABLE[(value >> 24) ^ byte]
    return value


def ogg_page(
    packets: list[bytes],
    granule: int,
    sequence: int,
    flags: int = 0,
    serial: int = OGG_SERIAL,
) -> bytes:
    """One page holding whole packets, with its checksum."""

    lacing: bytes = b""
    for packet in packets:
        lacing += b"\xff" * (len(packet) // 255) + bytes((len(packet) % 255,))
    header: bytes = (
        b"OggS"
        + bytes((0, flags))
        + struct.pack("<qIII", granule, serial, sequence, 0)
        + bytes((len(lacing),))
    )
    page: bytes = header + lacing + b"".join(packets)
    return page[:22] + struct.pack("<I", ogg_crc(page)) + page[26:]


def ogg_opus_recording(
    seconds: int,
    packets_per_page: int = 50,
    last_granule: int | None = None,
    serial: int = OGG_SERIAL,
) -> bytes:
    """
    An Ogg Opus stream of `seconds` of 20 ms packets, ending its stream;
    `last_granule` forges the last page's granule position.
    """

    pages: list[bytes] = [
        ogg_page([OPUS_HEAD], 0, 0, BEGINS, serial),
        ogg_page([OPUS_TAGS], 0, 1, 0, serial),
    ]
    total: int = seconds * PACKETS_PER_SECOND_20_MS
    for first in range(0, total, packets_per_page):
        count: int = min(packets_per_page, total - first)
        is_last: bool = first + count >= total
        # The pre-skip lies within the packets, as encoders count it.
        granule: int = (first + count) * 960
        if is_last and last_granule is not None:
            granule = last_granule
        pages.append(
            ogg_page(
                [OPUS_20_MS] * count,
                granule,
                len(pages),
                ENDS if is_last else 0,
                serial,
            )
        )
    return b"".join(pages)


def ogg_theora_bytes() -> bytes:
    """An Ogg stream whose first packet is a Theora video header."""

    return ogg_page([b"\x80theora" + bytes(40)], 0, 0, BEGINS)
