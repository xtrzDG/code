"""
Tidying the collected text of a page: invisible characters out, spaces
collapsed, empty and repeated lines dropped, the length capped.

Format characters (zero-width spaces and joiners, bidirectional controls,
Unicode tag characters) are removed: a visitor does not see them, and
they are a way to smuggle instructions to a model.
"""

import re
import unicodedata

SPACES: re.Pattern[str] = re.compile(r"[ \t\r\f\v  -   　]+")
CELL_SEPARATOR: str = " | "
TRUNCATION_MARK: str = "\n[…]"


def drop_invisible_characters(text: str) -> str:
    """Text without format and control characters (newlines and tabs stay)."""

    return "".join(
        character
        for character in text
        if character in "\n\t"
        or unicodedata.category(character) not in ("Cf", "Cc", "Co", "Cs")
    )


def clean_inline_text(text: str, keep_edges: bool = False) -> str:
    """One line of running text: invisible characters out, spaces collapsed."""

    collapsed: str = SPACES.sub(" ", drop_invisible_characters(text).replace("\n", " "))
    return collapsed if keep_edges else collapsed.strip()


def finish_text(parts: list[str], max_characters: int) -> str:
    """The page's lines, tidied, at most `max_characters` (cut between lines)."""

    lines: list[str] = []
    for raw_line in "".join(parts).split("\n"):
        line: str = tidy_line(raw_line)
        if line == "" or (lines and lines[-1] == line):
            continue

        lines.append(line)

    text: str = "\n".join(lines)
    if len(text) <= max_characters:
        return text

    cut: str = text[: max_characters - len(TRUNCATION_MARK)]
    last_break: int = cut.rfind("\n")
    if last_break > max_characters // 2:
        cut = cut[:last_break]

    return cut + TRUNCATION_MARK


def tidy_line(line: str) -> str:
    """Collapse spaces and trim a line, and the cell separators around it."""

    tidy: str = SPACES.sub(" ", drop_invisible_characters(line)).strip()
    while tidy.startswith("|"):
        tidy = tidy[1:].strip()
    while tidy.endswith("|"):
        tidy = tidy[:-1].strip()

    return re.sub(r"(\s*\|\s*)+", CELL_SEPARATOR, tidy)
