"""
Files of the demo customers' voice notes and photos, drawn here so the demo
needs no binary fixtures: a short voice-like sound (WAV) and a picture of a
khachapuri on a plate (PNG). Both are small and always the same.
"""

import math
import struct
import zlib

VOICE_SAMPLE_RATE: int = 8000
SYLLABLES_PER_SECOND: float = 3.6
PHOTO_WIDTH: int = 320
PHOTO_HEIGHT: int = 240
PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"

type Color = tuple[int, int, int]

TABLE_LIGHT: Color = (176, 122, 78)
TABLE_DARK: Color = (132, 86, 52)
PLATE: Color = (244, 241, 234)
PLATE_RIM: Color = (220, 214, 202)
CRUST: Color = (214, 150, 66)
CHEESE: Color = (250, 214, 112)
YOLK: Color = (242, 160, 30)


def build_demo_voice_note(seconds: int) -> bytes:
    """
    A WAV voice note `seconds` long (8 kHz, 8-bit mono): a voice-like hum
    whose pitch drifts and whose loudness rises and falls in syllables.
    """

    sample_count: int = seconds * VOICE_SAMPLE_RATE
    samples: bytearray = bytearray(sample_count)
    phase: float = 0.0
    for index in range(sample_count):
        moment: float = index / VOICE_SAMPLE_RATE
        pitch: float = 150.0 + 35.0 * math.sin(2 * math.pi * 0.7 * moment)
        phase += 2 * math.pi * pitch / VOICE_SAMPLE_RATE
        syllable: float = max(0.0, math.sin(math.pi * SYLLABLES_PER_SECOND * moment))
        fade: float = min(1.0, moment * 4, (seconds - moment) * 4)
        wave: float = (
            0.6 * math.sin(phase)
            + 0.3 * math.sin(2 * phase)
            + 0.1 * math.sin(3 * phase)
        )
        samples[index] = 128 + round(90 * wave * syllable * fade)

    return wav_file(bytes(samples))


def wav_file(samples: bytes) -> bytes:
    """8-bit mono PCM samples in a RIFF/WAVE container."""

    header: bytes = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(samples),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        VOICE_SAMPLE_RATE,
        VOICE_SAMPLE_RATE,
        1,
        8,
        b"data",
        len(samples),
    )
    return header + samples


def build_demo_dish_photo() -> bytes:
    """A PNG photo: an Adjarian khachapuri with its yolk on a white plate."""

    rows: list[bytes] = []
    for y in range(PHOTO_HEIGHT):
        row: bytearray = bytearray(b"\x00")
        for x in range(PHOTO_WIDTH):
            row.extend(dish_pixel(x, y))
        rows.append(bytes(row))

    return png_file(PHOTO_WIDTH, PHOTO_HEIGHT, b"".join(rows))


def dish_pixel(x: int, y: int) -> Color:
    center_x, center_y = PHOTO_WIDTH / 2, PHOTO_HEIGHT / 2
    plate: float = ((x - center_x) / 128) ** 2 + ((y - center_y) / 100) ** 2
    boat: float = ((x - center_x) / 104) ** 2 + ((y - center_y) / 46) ** 2
    filling: float = ((x - center_x) / 72) ** 2 + ((y - center_y) / 26) ** 2
    yolk: float = ((x - center_x - 6) / 15) ** 2 + ((y - center_y + 2) / 13) ** 2
    if yolk <= 1:
        return YOLK
    if filling <= 1:
        return CHEESE
    if boat <= 1:
        return CRUST
    if plate <= 0.86:
        return PLATE
    if plate <= 1:
        return PLATE_RIM
    return TABLE_DARK if (x // 40 + y // 12) % 5 == 0 else TABLE_LIGHT


def png_file(width: int, height: int, filtered_rows: bytes) -> bytes:
    """An 8-bit RGB PNG from rows that each start with filter byte 0."""

    header: bytes = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(filtered_rows, 9))
        + png_chunk(b"IEND", b"")
    )


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )
