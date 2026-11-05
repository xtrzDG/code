"""
Small, structurally real MP4 recordings built byte by byte: AAC as Safari
records it or Opus as Chromium can, in plain sample tables or in movie
fragments, honest or with forged durations.
"""

import struct
from dataclasses import dataclass

AAC_RATE: int = 48_000
AAC_FRAME: int = 1024
OPUS_PACKET_20_MS: bytes = b"\xf8\x11\x22\x33"
OPUS_PACKET_SAMPLES: int = 960
# AudioSpecificConfig: AAC LC (2), 48 kHz (index 3), mono.
AAC_LC_48K_MONO: bytes = b"\x11\x88"


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def full_box(kind: bytes, payload: bytes, version: int = 0, flags: int = 0) -> bytes:
    return box(kind, struct.pack(">I", version << 24 | flags) + payload)


def descriptor(tag: int, body: bytes) -> bytes:
    return bytes((tag, len(body))) + body


def esds(config: bytes = AAC_LC_48K_MONO, object_type: int = 0x40) -> bytes:
    decoder_config: bytes = descriptor(
        0x04,
        bytes((object_type, 0x15)) + bytes(11) + descriptor(0x05, config),
    )
    return full_box(
        b"esds",
        descriptor(0x03, b"\x00\x01\x00" + decoder_config + descriptor(0x06, b"\x02")),
    )


def sample_entry(codec: str) -> bytes:
    """An 'mp4a' entry with its decoder config, or an 'Opus' one."""

    audio_fields: bytes = bytes(6) + struct.pack(">H", 1) + bytes(8)
    audio_fields += struct.pack(">HHHHI", 1, 16, 0, 0, AAC_RATE << 16)
    if codec == "opus":
        return box(b"Opus", audio_fields + box(b"dOps", bytes(11)))
    if codec == "mp3":
        return box(b".mp3", audio_fields)
    return box(b"mp4a", audio_fields + esds())


@dataclass(frozen=True)
class Mp4Plan:
    """What to write: how much audio, and what the headers claim."""

    samples: int
    sample_bytes: bytes
    rate: int
    sample_ticks: int
    claimed_ticks: int


def plan(seconds: int, codec: str, claimed_seconds: int | None) -> Mp4Plan:
    if codec == "opus":
        count: int = seconds * AAC_RATE // OPUS_PACKET_SAMPLES
        ticks: int = OPUS_PACKET_SAMPLES
        sample: bytes = OPUS_PACKET_20_MS
    else:
        count = seconds * AAC_RATE // AAC_FRAME
        ticks = AAC_FRAME
        sample = b"\x21\x00\x49\x90"
    claimed: int = (
        count * ticks if claimed_seconds is None else claimed_seconds * AAC_RATE
    )
    return Mp4Plan(count, sample, AAC_RATE, max(1, claimed // max(count, 1)), claimed)


def track(
    handler: bytes,
    codec: str,
    tables: bytes,
    claimed_ticks: int,
    track_id: int = 1,
    edits: bytes = b"",
) -> bytes:
    header: bytes = full_box(
        b"tkhd",
        struct.pack(">IIIII", 0, 0, track_id, 0, claimed_ticks) + bytes(60),
        0,
        3,
    )
    media_header: bytes = full_box(
        b"mdhd", struct.pack(">IIII", 0, 0, AAC_RATE, claimed_ticks) + bytes(4)
    )
    handler_box: bytes = full_box(
        b"hdlr", bytes(4) + handler + bytes(12) + b"sound\x00"
    )
    sample_table: bytes = box(
        b"stbl", full_box(b"stsd", struct.pack(">I", 1) + sample_entry(codec)) + tables
    )
    media: bytes = box(
        b"mdia",
        media_header
        + handler_box
        + box(b"minf", full_box(b"smhd", bytes(4)) + sample_table),
    )
    return box(b"trak", header + edits + media)


def movie(claimed_ticks: int, tracks: bytes, extends: bytes = b"") -> bytes:
    header: bytes = full_box(
        b"mvhd", struct.pack(">IIII", 0, 0, AAC_RATE, claimed_ticks) + bytes(80)
    )
    return box(b"moov", header + tracks + extends)


def mp4_recording(
    seconds: int,
    handlers: tuple[bytes, ...] = (b"soun",),
    codec: str = "aac",
    claimed_seconds: int | None = None,
    edits: bytes = b"",
) -> bytes:
    """
    An M4A as Safari records it: plain sample tables, one chunk, the movie
    and track headers and the time-to-sample table claiming
    `claimed_seconds` (the truth unless given), one track per handler.
    """

    shape: Mp4Plan = plan(seconds, codec, claimed_seconds)
    file_type: bytes = box(b"ftyp", b"M4A " + bytes(4) + b"isomM4A ")
    data: bytes = shape.sample_bytes * shape.samples

    def tables(chunk_offset: int) -> bytes:
        return (
            full_box(b"stts", struct.pack(">III", 1, shape.samples, shape.sample_ticks))
            + full_box(b"stsc", struct.pack(">IIII", 1, 1, shape.samples, 1))
            + full_box(
                b"stsz",
                struct.pack(">II", 0, shape.samples)
                + struct.pack(">I", len(shape.sample_bytes)) * shape.samples,
            )
            + full_box(b"stco", struct.pack(">II", 1, chunk_offset))
        )

    def build(chunk_offset: int) -> bytes:
        tracks: bytes = b"".join(
            track(
                kind, codec, tables(chunk_offset), shape.claimed_ticks, index + 1, edits
            )
            for index, kind in enumerate(handlers)
        )
        return file_type + movie(shape.claimed_ticks, tracks)

    head: bytes = build(0)
    return build(len(head) + 8) + box(b"mdat", data)


def fragmented_mp4_recording(
    seconds: int, codec: str = "opus", claimed_seconds: int | None = None
) -> bytes:
    """
    A fragmented MP4 as Chromium records it: an empty sample table, the
    track's defaults in 'mvex', one fragment whose run gives each sample's
    duration (summing to `claimed_seconds` when given) and size.
    """

    shape: Mp4Plan = plan(seconds, codec, claimed_seconds)
    empty_tables: bytes = (
        full_box(b"stts", struct.pack(">I", 0))
        + full_box(b"stsc", struct.pack(">I", 0))
        + full_box(b"stsz", struct.pack(">II", 0, 0))
        + full_box(b"stco", struct.pack(">I", 0))
    )
    extends: bytes = box(
        b"mvex", full_box(b"trex", struct.pack(">IIIII", 1, 1, 0, 0, 0))
    )
    head: bytes = box(b"ftyp", b"iso5" + bytes(4) + b"iso5mp41") + movie(
        0, track(b"soun", codec, empty_tables, 0), extends
    )
    entries: bytes = struct.pack(">II", shape.sample_ticks, len(shape.sample_bytes))
    entries *= shape.samples

    def fragment(data_offset: int) -> bytes:
        run: bytes = full_box(
            b"trun", struct.pack(">Ii", shape.samples, data_offset) + entries, 0, 0x301
        )
        header: bytes = full_box(b"tfhd", struct.pack(">I", 1), 0, 0x020000)
        decode_time: bytes = full_box(b"tfdt", struct.pack(">I", 0))
        return box(
            b"moof",
            full_box(b"mfhd", struct.pack(">I", 1))
            + box(b"traf", header + decode_time + run),
        )

    size: int = len(fragment(0))
    return head + fragment(size + 8) + box(b"mdat", shape.sample_bytes * shape.samples)


def edit_list(*durations: int) -> bytes:
    """An edit list of edits of `durations` (movie ticks) from media time 0."""

    entries: bytes = b"".join(
        struct.pack(">Iii", ticks, 0, 1 << 16) for ticks in durations
    )
    return box(b"edts", full_box(b"elst", struct.pack(">I", len(durations)) + entries))
