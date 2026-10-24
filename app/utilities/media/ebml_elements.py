"""
The variable-length integers of EBML (WebM, Matroska): element ids and
data sizes, read without decoding the file.
"""

LONGEST_ID_BYTES: int = 4
LONGEST_SIZE_BYTES: int = 8


class WebmStructureError(ValueError):
    """The file is not a WebM structure this reader walks."""


def read_id(content: bytes, position: int) -> tuple[int, int]:
    """An element id (its length marker kept) and the position after it."""

    length: int = vint_length(content[position], LONGEST_ID_BYTES)
    return int.from_bytes(
        content[position : position + length], "big"
    ), position + length


def read_size(content: bytes, position: int) -> tuple[int | None, int]:
    """A data size (None: unknown, all ones) and the position after it."""

    first: int = content[position]
    length: int = vint_length(first, LONGEST_SIZE_BYTES)
    value: int = first & (0xFF >> length)
    for index in range(1, length):
        value = (value << 8) | content[position + index]
    is_unknown: bool = value == (1 << (7 * length)) - 1
    return (None if is_unknown else value), position + length


def vint_length(first: int, longest: int) -> int:
    """How many bytes a variable-length integer takes, from its first byte."""

    for length in range(1, longest + 1):
        if first & (0x80 >> (length - 1)):
            return length

    raise WebmStructureError("Not an EBML variable-length integer.")
