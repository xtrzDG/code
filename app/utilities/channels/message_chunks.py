"""Splitting long replies to the length limit of a messaging platform."""

# Preferred break points, best first: paragraph, line, sentence, word.
BREAK_SEPARATORS: tuple[str, ...] = (
    "\n\n",
    "\n",
    ". ",
    "! ",
    "? ",
    "。",
    "؟ ",
    "। ",
    " ",
)
# A break this early would leave a tiny first part; cut harder instead.
MIN_BREAK_FRACTION: float = 0.5


def utf16_length(text: str) -> int:
    """Length in UTF-16 code units, the unit platforms count limits in."""

    return len(text.encode("utf-16-le")) // 2


def split_message_text(text: str, limit: int) -> list[str]:
    """
    Split `text` into parts of at most `limit` UTF-16 code units, breaking at
    paragraphs, lines, sentences or spaces when possible and never inside a
    character. Blank parts are dropped; text within the limit is one part.
    """

    if limit < 1:
        raise ValueError("The message length limit must be positive.")

    remaining: str = text.strip()
    parts: list[str] = []
    while remaining != "":
        if utf16_length(remaining) <= limit:
            parts.append(remaining)
            break

        hard_end: int = longest_prefix_within(remaining, limit)
        cut: int = find_break(remaining[:hard_end], hard_end)
        part: str = remaining[:cut].strip()
        if part != "":
            parts.append(part)

        remaining = remaining[cut:].strip()

    return parts


def longest_prefix_within(text: str, limit: int) -> int:
    """Number of characters of the longest prefix within `limit` code units."""

    used_units: int = 0
    for index, character in enumerate(text):
        character_units: int = 2 if ord(character) > 0xFFFF else 1
        if used_units + character_units > limit:
            return max(index, 1)

        used_units += character_units

    return len(text)


def find_break(window: str, hard_end: int) -> int:
    """Index after the best separator in `window`, or `hard_end`."""

    minimum_cut: int = int(hard_end * MIN_BREAK_FRACTION)
    for separator in BREAK_SEPARATORS:
        position: int = window.rfind(separator)
        if position >= minimum_cut and position > 0:
            return position + len(separator)

    return hard_end
