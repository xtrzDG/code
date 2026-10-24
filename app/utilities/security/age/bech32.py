"""
Bech32 (BIP 173), the text form of age keys.

age writes its X25519 recipients (`age1...`) and identities
(`AGE-SECRET-KEY-1...`) in Bech32 without the 90-character limit of
Bitcoin addresses. Only what age needs is here: 8-bit data in, 8-bit data
out, one checksum (not Bech32m).
"""

CHARSET: str = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
CHARSET_INDEX: dict[str, int] = {char: index for index, char in enumerate(CHARSET)}
GENERATOR: tuple[int, ...] = (
    0x3B6A57B2,
    0x26508E6D,
    0x1EA119FA,
    0x3D4233DD,
    0x2A1462B3,
)
CHECKSUM_LENGTH: int = 6
SEPARATOR: str = "1"


class Bech32Error(ValueError):
    """The text is not valid Bech32 (or not the expected human-readable part)."""


def bech32_encode(human_readable_part: str, data: bytes) -> str:
    """Lowercase Bech32 of `data` under the human-readable part."""

    words: list[int] = convert_bits(data, 8, 5, pad=True)
    checksum: list[int] = create_checksum(human_readable_part, words)
    return (
        human_readable_part
        + SEPARATOR
        + "".join(CHARSET[word] for word in words + checksum)
    )


def bech32_decode(text: str, human_readable_part: str) -> bytes:
    """
    The data of a Bech32 string whose human-readable part is the expected
    one (compared without case). Mixed case, a wrong checksum, characters
    outside the alphabet or leftover bits are refused with Bech32Error.
    """

    if text != text.lower() and text != text.upper():
        raise Bech32Error("Bech32 text mixes upper and lower case.")

    lowered: str = text.lower()
    separator_index: int = lowered.rfind(SEPARATOR)
    if separator_index < 1 or len(lowered) - separator_index - 1 < CHECKSUM_LENGTH:
        raise Bech32Error("Bech32 text has no separator or no checksum.")

    prefix: str = lowered[:separator_index]
    if prefix != human_readable_part.lower():
        raise Bech32Error(f"Expected a key starting with {human_readable_part!r}.")

    words: list[int] = []
    for char in lowered[separator_index + 1 :]:
        word: int | None = CHARSET_INDEX.get(char)
        if word is None:
            raise Bech32Error("Bech32 text has a character outside its alphabet.")
        words.append(word)

    if polymod(expand_human_readable_part(prefix) + words) != 1:
        raise Bech32Error("Bech32 checksum does not match.")

    return bytes(convert_bits(words[:-CHECKSUM_LENGTH], 5, 8, pad=False))


def convert_bits(
    values: bytes | list[int],
    from_bits: int,
    to_bits: int,
    pad: bool,
) -> list[int]:
    """Regroup a sequence of `from_bits`-bit values into `to_bits`-bit ones."""

    accumulator: int = 0
    bit_count: int = 0
    result: list[int] = []
    max_value: int = (1 << to_bits) - 1
    for value in values:
        accumulator = (accumulator << from_bits) | value
        bit_count += from_bits
        while bit_count >= to_bits:
            bit_count -= to_bits
            result.append((accumulator >> bit_count) & max_value)

    if pad:
        if bit_count > 0:
            result.append((accumulator << (to_bits - bit_count)) & max_value)
    elif bit_count >= from_bits or (accumulator << (to_bits - bit_count)) & max_value:
        raise Bech32Error("Bech32 data has leftover bits.")

    return result


def create_checksum(human_readable_part: str, words: list[int]) -> list[int]:
    values: list[int] = expand_human_readable_part(human_readable_part) + words
    remainder: int = polymod([*values, *([0] * CHECKSUM_LENGTH)]) ^ 1
    return [
        (remainder >> (5 * (CHECKSUM_LENGTH - 1 - index))) & 31
        for index in range(CHECKSUM_LENGTH)
    ]


def expand_human_readable_part(human_readable_part: str) -> list[int]:
    return (
        [ord(char) >> 5 for char in human_readable_part]
        + [0]
        + [ord(char) & 31 for char in human_readable_part]
    )


def polymod(values: list[int]) -> int:
    checksum: int = 1
    for value in values:
        top: int = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(GENERATOR):
            if (top >> index) & 1:
                checksum ^= generator

    return checksum
