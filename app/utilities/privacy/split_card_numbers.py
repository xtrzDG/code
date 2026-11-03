"""
A card number a caller reads out over several turns ("4242 4242", the
agent's "go on", "4242 4242 4242"): no line holds enough digits to be
masked on its own (`mask_sensitive_numbers`), so the caller's lines are
read together, the digits that end one line joined with the digits that
start the next, and each piece of a card found that way is masked in its
own line. Words between the digits ("my number is 347 123 4567", "for 4
people") end a run, so only lines that end and start with digits join.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.utilities.privacy.sensitive_numbers import (
    CARD_PLACEHOLDER,
    DIGIT_RUN_PATTERN,
    is_card_run,
)

LINE_JOINER: str = "\n"
# What a speech recognizer puts around a line's words: spaces and the
# sentence's punctuation ("4242 4242.", "... 4242 4242").
LINE_EDGE_CHARACTERS: str = " \t\n\r\u00a0\u2009\u202f.,;:!?\u2026"


@dataclass(frozen=True)
class LineCore:
    """A line without its edges and where that core starts in the line."""

    text: str
    offset: int


def mask_split_card_numbers(lines: Sequence[str]) -> list[str]:
    """
    The caller's lines, in order, with the pieces of a card number read out
    over several of them masked; a line keeps everything else.
    """

    cores: list[LineCore] = [line_core(line) for line in lines]
    joined: str = LINE_JOINER.join(core.text for core in cores)
    starts: list[int] = core_starts(cores)
    pieces: dict[int, list[tuple[int, int]]] = {}
    for match in DIGIT_RUN_PATTERN.finditer(joined):
        first: int = line_of(starts, match.start())
        last: int = line_of(starts, match.end() - 1)
        if first == last or not is_card_run(match.group(0)):
            continue

        for index in range(first, last + 1):
            start: int = max(match.start(), starts[index]) - starts[index]
            end: int = min(match.end(), starts[index] + len(cores[index].text))
            pieces.setdefault(index, []).append(
                (start + cores[index].offset, end - starts[index] + cores[index].offset)
            )

    return [
        mask_pieces(line, pieces.get(index, [])) for index, line in enumerate(lines)
    ]


def line_core(line: str) -> LineCore:
    leading: int = len(line) - len(line.lstrip(LINE_EDGE_CHARACTERS))
    return LineCore(text=line.strip(LINE_EDGE_CHARACTERS), offset=leading)


def core_starts(cores: list[LineCore]) -> list[int]:
    """Where each line's core starts in the joined text."""

    starts: list[int] = []
    position: int = 0
    for core in cores:
        starts.append(position)
        position += len(core.text) + len(LINE_JOINER)

    return starts


def line_of(starts: list[int], position: int) -> int:
    """The line a position of the joined text belongs to."""

    index: int = 0
    for line_index, start in enumerate(starts):
        if start <= position:
            index = line_index

    return index


def mask_pieces(line: str, pieces: list[tuple[int, int]]) -> str:
    for start, end in sorted(pieces, reverse=True):
        line = line[:start] + CARD_PLACEHOLDER + line[end:]

    return line
