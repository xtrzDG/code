"""
The one piece of a photo's Exif block worth keeping: how to turn it.

Phones store a photo as the sensor saw it and say in Exif how to rotate it
for display (the Orientation tag, 1 to 8). Everything else in Exif (where
and when it was taken, the device, its serial number, a thumbnail) is
personal data a customer never meant to send, so uploads keep only this tag,
in a minimal Exif block of its own.
"""

import struct

EXIF_HEADER: bytes = b"Exif\x00\x00"
ORIENTATION_TAG: int = 0x0112
SHORT_TYPE: int = 3
IFD_ENTRY_SIZE: int = 12
UPRIGHT: int = 1
LARGEST_ORIENTATION: int = 8
BYTE_ORDERS: dict[bytes, str] = {b"II": "<", b"MM": ">"}
TIFF_MAGIC: int = 42


def read_exif_orientation(app1_payload: bytes) -> int | None:
    """
    The Orientation (2 to 8) of a JPEG APP1 Exif payload; None when the
    photo is upright, has no such tag, or the block does not parse.
    """

    if not app1_payload.startswith(EXIF_HEADER):
        return None

    tiff: bytes = app1_payload[len(EXIF_HEADER) :]
    byte_order: str | None = BYTE_ORDERS.get(tiff[:2])
    if byte_order is None or len(tiff) < 8:
        return None

    magic, first_ifd = struct.unpack_from(f"{byte_order}HI", tiff, 2)
    if magic != TIFF_MAGIC or first_ifd + 2 > len(tiff):
        return None

    (entry_count,) = struct.unpack_from(f"{byte_order}H", tiff, first_ifd)
    for index in range(entry_count):
        entry_at: int = first_ifd + 2 + index * IFD_ENTRY_SIZE
        if entry_at + IFD_ENTRY_SIZE > len(tiff):
            return None

        tag, value_type, count = struct.unpack_from(f"{byte_order}HHI", tiff, entry_at)
        if tag != ORIENTATION_TAG:
            continue

        if value_type != SHORT_TYPE or count != 1:
            return None

        (orientation,) = struct.unpack_from(f"{byte_order}H", tiff, entry_at + 8)
        is_turned: bool = UPRIGHT < orientation <= LARGEST_ORIENTATION
        return orientation if is_turned else None

    return None


def orientation_only_exif(orientation: int) -> bytes:
    """
    The APP1 payload of an Exif block that holds the Orientation and nothing
    else (big-endian TIFF, one IFD with one entry, no next IFD).
    """

    entry: bytes = struct.pack(">HHIHH", ORIENTATION_TAG, SHORT_TYPE, 1, orientation, 0)
    tiff: bytes = (
        struct.pack(">2sHI", b"MM", TIFF_MAGIC, 8)
        + struct.pack(">H", 1)
        + entry
        + struct.pack(">I", 0)
    )
    return EXIF_HEADER + tiff
