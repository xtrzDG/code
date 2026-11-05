"""
Writing exported tables as CSV a spreadsheet opens safely and correctly.

- UTF-8 with a byte order mark first, so Excel reads Georgian and Cyrillic
  instead of guessing a legacy code page;
- RFC 4180 quoting (a comma, a quote or a line break inside a value);
- formula injection defused: a value a spreadsheet would run as a formula
  (it starts with =, +, -, @, a tab or a carriage return, also after
  leading spaces) gets a leading apostrophe, so "=HYPERLINK(...)" typed by
  a customer stays text (OWASP "CSV Injection").
"""

import csv
import io
from collections.abc import Sequence

UTF8_BOM: str = "﻿"
FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")
LINE_TERMINATOR: str = "\r\n"


def escape_cell(value: str) -> str:
    """The value as a spreadsheet must show it: never as a formula."""

    if value.lstrip(" ").startswith(FORMULA_PREFIXES):
        return "'" + value

    return value


def csv_line(cells: Sequence[str]) -> str:
    """One row as a CSV line (escaped, quoted where needed, CRLF ended)."""

    buffer = io.StringIO()
    writer = csv.writer(
        buffer, quoting=csv.QUOTE_MINIMAL, lineterminator=LINE_TERMINATOR
    )
    writer.writerow([escape_cell(cell) for cell in cells])
    return buffer.getvalue()
