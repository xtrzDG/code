"""
The sampling rate an AAC decoder runs at, read from the decoder config an
MP4 sound track carries (its 'esds' box: an ES descriptor whose decoder
config descriptor holds the AudioSpecificConfig, ISO/IEC 14496-1 and -3).

An AAC frame decodes to 1024 samples of the core rate, the first rate the
config names (with explicit SBR signalling, the extension rate doubles the
samples and the rate together), whatever the container's timing tables
say. Other audio in MP4 (MP3, ALS, USAC) is not a voice note here.
"""

from app.utilities.media.mp4_boxes import Mp4StructureError

ES_DESCRIPTOR: int = 0x03
DECODER_CONFIG_DESCRIPTOR: int = 0x04
DECODER_SPECIFIC_DESCRIPTOR: int = 0x05
# ES_Descriptor flags: a stream it depends on, a URL, an OCR stream id.
DEPENDS_ON_STREAM: int = 0x80
HAS_URL: int = 0x40
HAS_OCR_STREAM: int = 0x20
ES_HEADER_BYTES: int = 3
DECODER_CONFIG_HEADER_BYTES: int = 13
LONGEST_DESCRIPTOR_SIZE_BYTES: int = 4
# objectTypeIndication: MPEG-4 audio, MPEG-2 AAC (main, LC, SSR).
AAC_OBJECT_TYPE_INDICATIONS: frozenset[int] = frozenset({0x40, 0x66, 0x67, 0x68})
# audioObjectType of the AAC family, low-delay variants included.
AAC_AUDIO_OBJECT_TYPES: frozenset[int] = frozenset(
    {1, 2, 3, 4, 5, 6, 17, 19, 20, 21, 22, 23, 29, 39}
)
ESCAPED_OBJECT_TYPE: int = 31
EXPLICIT_RATE_INDEX: int = 15
AAC_RATES: tuple[int, ...] = (
    96000,
    88200,
    64000,
    48000,
    44100,
    32000,
    24000,
    22050,
    16000,
    12000,
    11025,
    8000,
    7350,
)
AAC_FRAME_SAMPLES: int = 1024
# Object type (5 + 6 bits) and rate (4 + 24 bits) fit in five bytes.
CONFIG_HEAD_BYTES: int = 5


def read_aac_core_rate(descriptors: bytes) -> int:
    """
    The core sampling rate of the AAC config in an 'esds' box's body.

    Raises:
        Mp4StructureError: no AAC decoder config, or one that does not parse.
    """

    tag, start, end = read_descriptor(descriptors, 0)
    if tag != ES_DESCRIPTOR or start + ES_HEADER_BYTES > end:
        raise Mp4StructureError("The track's decoder config is missing.")

    flags: int = descriptors[start + 2]
    position: int = start + ES_HEADER_BYTES
    if flags & DEPENDS_ON_STREAM:
        position += 2
    if flags & HAS_URL:
        position += 1 + descriptors[position]
    if flags & HAS_OCR_STREAM:
        position += 2

    config_start, config_end = find_descriptor(
        descriptors, position, end, DECODER_CONFIG_DESCRIPTOR
    )
    if config_start + DECODER_CONFIG_HEADER_BYTES > config_end or (
        descriptors[config_start] not in AAC_OBJECT_TYPE_INDICATIONS
    ):
        raise Mp4StructureError("The track's audio is not AAC.")

    specific_start, specific_end = find_descriptor(
        descriptors,
        config_start + DECODER_CONFIG_HEADER_BYTES,
        config_end,
        DECODER_SPECIFIC_DESCRIPTOR,
    )
    return read_audio_specific_config(descriptors[specific_start:specific_end])


def read_audio_specific_config(config: bytes) -> int:
    """The core rate of an AudioSpecificConfig of the AAC family."""

    head: int = int.from_bytes(config[:CONFIG_HEAD_BYTES].ljust(5, b"\x00"), "big")
    available_bits: int = 8 * min(len(config), CONFIG_HEAD_BYTES)
    position: int = 0

    def take(count: int) -> int:
        nonlocal position
        if position + count > available_bits:
            raise Mp4StructureError("The AAC config is cut short.")
        value: int = (head >> (8 * CONFIG_HEAD_BYTES - position - count)) & (
            (1 << count) - 1
        )
        position += count
        return value

    object_type: int = take(5)
    if object_type == ESCAPED_OBJECT_TYPE:
        object_type = 32 + take(6)
    rate_index: int = take(4)
    rate: int = (
        take(24)
        if rate_index == EXPLICIT_RATE_INDEX
        else (AAC_RATES[rate_index] if rate_index < len(AAC_RATES) else 0)
    )
    if object_type not in AAC_AUDIO_OBJECT_TYPES or rate <= 0:
        raise Mp4StructureError("The track's audio is not AAC.")

    return rate


def find_descriptor(data: bytes, start: int, end: int, wanted: int) -> tuple[int, int]:
    """The body of the first descriptor of a tag between `start` and `end`."""

    position: int = start
    while position < end:
        tag, body_start, body_end = read_descriptor(data, position)
        if body_end > end:
            raise Mp4StructureError("A descriptor runs past its parent.")
        if tag == wanted:
            return body_start, body_end
        position = body_end

    raise Mp4StructureError("A decoder descriptor is missing.")


def read_descriptor(data: bytes, at: int) -> tuple[int, int, int]:
    """A descriptor's tag, and where its body begins and ends."""

    tag: int = data[at]
    size: int = 0
    position: int = at + 1
    for _ in range(LONGEST_DESCRIPTOR_SIZE_BYTES):
        byte: int = data[position]
        position += 1
        size = (size << 7) | (byte & 0x7F)
        if not byte & 0x80:
            break

    if position + size > len(data):
        raise Mp4StructureError("A descriptor runs past its box.")

    return tag, position, position + size
