"""
How long a voice note is, read from its container without decoding it:
Ogg (Opus, Vorbis: the last page's granule position), MP4 and M4A (the
movie header), WAV (data size over byte rate). Other formats, and files
these readers do not understand, have no known duration (None).
"""

import math
import struct

OGG_CAPTURE: bytes = b"OggS"
OGG_GRANULE_OFFSET: int = 6
OPUS_HEAD: bytes = b"OpusHead"
OPUS_SAMPLE_RATE: int = 48_000
VORBIS_HEAD: bytes = b"\x01vorbis"
VORBIS_RATE_OFFSET: int = 12
MVHD_BOX: bytes = b"mvhd"
WAV_FMT: bytes = b"fmt "
WAV_DATA: bytes = b"data"
OGG_TAIL_BYTES: int = 64 * 1024


def read_audio_duration_seconds(content: bytes) -> int | None:
    """Whole seconds, rounded up; None when the container does not tell."""

    seconds: float | None = None
    if content.startswith(OGG_CAPTURE):
        seconds = read_ogg_seconds(content)
    elif content[4:8] == b"ftyp":
        seconds = read_mp4_seconds(content)
    elif content.startswith(b"RIFF") and content[8:12] == b"WAVE":
        seconds = read_wav_seconds(content)

    if seconds is None or seconds < 0 or not math.isfinite(seconds):
        return None

    return math.ceil(seconds)


def read_ogg_seconds(content: bytes) -> float | None:
    sample_rate: int | None = read_ogg_sample_rate(content)
    last_page: int = content.rfind(OGG_CAPTURE, max(0, len(content) - OGG_TAIL_BYTES))
    granule_end: int = last_page + OGG_GRANULE_OFFSET + 8
    if sample_rate is None or last_page < 0 or granule_end > len(content):
        return None

    (granule,) = struct.unpack_from("<q", content, last_page + OGG_GRANULE_OFFSET)
    return None if granule < 0 else granule / sample_rate


def read_ogg_sample_rate(content: bytes) -> int | None:
    head: bytes = content[:512]
    if head.find(OPUS_HEAD) >= 0:
        # Opus granule positions always count 48 kHz samples.
        return OPUS_SAMPLE_RATE

    vorbis_at: int = head.find(VORBIS_HEAD)
    rate_at: int = vorbis_at + VORBIS_RATE_OFFSET
    if vorbis_at < 0 or rate_at + 4 > len(head):
        return None

    (rate,) = struct.unpack_from("<I", head, rate_at)
    return rate or None


def read_mp4_seconds(content: bytes) -> float | None:
    box_at: int = content.find(MVHD_BOX)
    if box_at < 4:
        return None

    version_at: int = box_at + 4
    if version_at >= len(content):
        return None

    try:
        if content[version_at] == 1:
            timescale, duration = struct.unpack_from(">IQ", content, version_at + 20)
        else:
            timescale, duration = struct.unpack_from(">II", content, version_at + 12)
    except struct.error:
        return None

    return None if timescale == 0 else duration / timescale


def read_wav_seconds(content: bytes) -> float | None:
    format_at: int = content.find(WAV_FMT, 12)
    data_at: int = content.find(WAV_DATA, 12)
    if format_at < 0 or data_at < 0:
        return None

    try:
        (byte_rate,) = struct.unpack_from("<I", content, format_at + 16)
        (data_size,) = struct.unpack_from("<I", content, data_at + 4)
    except struct.error:
        return None

    return None if byte_rate == 0 else data_size / byte_rate
