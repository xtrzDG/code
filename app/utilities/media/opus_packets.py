"""
How much audio an Opus packet holds, read from its table-of-contents byte
(RFC 6716, section 3.1) without decoding it.

A container's timestamps and durations are claims its writer made; the
packets are what a decoder plays. Every packet says how long its frames
are and how many it holds, so the sum over a recording's packets is the
length a decoder produces, whatever the container claims.
"""

OPUS_SAMPLE_RATE: int = 48_000
# Frame lengths in 48 kHz samples by configuration (the TOC's top 5 bits):
# SILK 10/20/40/60 ms, Hybrid 10/20 ms, CELT 2.5/5/10/20 ms.
SILK_FRAMES: tuple[int, ...] = (480, 960, 1920, 2880)
HYBRID_FRAMES: tuple[int, ...] = (480, 960)
CELT_FRAMES: tuple[int, ...] = (120, 240, 480, 960)
FIRST_HYBRID_CONFIG: int = 12
FIRST_CELT_CONFIG: int = 16
ARBITRARY_FRAMES_CODE: int = 3
FRAME_COUNT_MASK: int = 0x3F
# No packet is longer than 120 ms (RFC 6716, 3.2.5).
LONGEST_PACKET_SAMPLES: int = 5760


def opus_packet_samples(packet: bytes) -> int | None:
    """
    The 48 kHz samples one Opus packet decodes to; None for bytes that are
    not an Opus packet (empty, no frame count, longer than 120 ms).
    """

    if not packet:
        return None

    toc: int = packet[0]
    frame_samples: int = frame_length(toc >> 3)
    code: int = toc & 0x03
    if code == 0:
        frames: int = 1
    elif code < ARBITRARY_FRAMES_CODE:
        frames = 2
    elif len(packet) < 2:
        return None
    else:
        frames = packet[1] & FRAME_COUNT_MASK

    samples: int = frame_samples * frames
    if frames == 0 or samples > LONGEST_PACKET_SAMPLES:
        return None

    return samples


def frame_length(config: int) -> int:
    """48 kHz samples of one frame of a TOC configuration (0 to 31)."""

    if config < FIRST_HYBRID_CONFIG:
        return SILK_FRAMES[config % len(SILK_FRAMES)]

    if config < FIRST_CELT_CONFIG:
        return HYBRID_FRAMES[config % len(HYBRID_FRAMES)]

    return CELT_FRAMES[config % len(CELT_FRAMES)]
