"""
Look for payment card numbers where the platform keeps none (PCI DSS SAQ
A, docs/security/payments.md): a data-only database dump, exported log
lines, a listing of the storage or any other text export, read line by
line and each tab-separated field on its own (a dump's columns), with the
check the masking applies (`app/utilities/privacy/sensitive_numbers.py`:
13 to 19 digits that pass the Luhn check and are not part of an id).
A hit is reported by file and line, never with its digits:

    pg_dump --data-only "$DATABASE_URL" > dump.sql
    uv run python -m scripts.card_number_scan dump.sql logs/*.jsonl

`-` reads the standard input. Exit codes: 0 no card number, 1 a card
number found (each hit is checked by hand: a Luhn-valid order number
looks the same), 2 a file that cannot be read.
"""

import argparse
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from app.utilities.privacy.sensitive_numbers import DIGIT_RUN_PATTERN, is_card_run

EXIT_CLEAN: int = 0
EXIT_FOUND: int = 1
EXIT_UNREADABLE: int = 2
STANDARD_INPUT: str = "-"
FIELD_SEPARATOR: str = "\t"


def count_card_numbers(line: str) -> int:
    """The card numbers of one line, each field of a dump on its own."""

    return sum(
        1
        for field in line.split(FIELD_SEPARATOR)
        for match in DIGIT_RUN_PATTERN.finditer(field)
        if is_card_run(match.group(0))
    )


def scan(name: str, lines: Iterable[str]) -> list[str]:
    """`name:line: N card number(s)` for each line that holds one."""

    hits: list[str] = []
    for number, line in enumerate(lines, start=1):
        found: int = count_card_numbers(line)
        if found:
            hits.append(f"{name}:{number}: {found} card number(s)")

    return hits


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find card numbers in exports.")
    parser.add_argument("files", nargs="+", help="text exports, or - for stdin")
    parsed = parser.parse_args(arguments)
    hits: list[str] = []
    for name in parsed.files:
        if name == STANDARD_INPUT:
            hits += scan(name, sys.stdin)
            continue

        try:
            with Path(name).open(encoding="utf-8", errors="replace") as export:
                hits += scan(name, export)
        except OSError as error:
            print(f"{name}: cannot be read ({error.strerror})", file=sys.stderr)
            return EXIT_UNREADABLE

    for hit in hits:
        print(hit)
    print(f"{len(hits)} line(s) with a card number in {len(parsed.files)} file(s).")
    return EXIT_FOUND if hits else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
