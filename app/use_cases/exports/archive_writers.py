"""
Incremental writers of a full export's files: a JSON array written one
document at a time and a CSV table written one row at a time, each into
an open entry of the archive, so a file of any length is never built in
memory.
"""

import json
from collections.abc import Iterable, Sequence
from typing import IO

from base_pydantic_schemas import BaseDocument

from app.schemas.dto.privacy.csv_exports import CsvRow
from app.utilities.privacy.csv_writing import UTF8_BOM, csv_line

# Fields that are keys to something, not data of the business.
SECRET_FIELDS: frozenset[str] = frozenset({"review_token"})
JSON_INDENT: int = 2
ELEMENT_PREFIX: str = " " * JSON_INDENT


def document_json(document: BaseDocument) -> str:
    """One document as an element of the file's array (indented, no secrets)."""

    text: str = json.dumps(
        document.model_dump(mode="json", exclude=set(SECRET_FIELDS)),
        ensure_ascii=False,
        indent=JSON_INDENT,
    )
    return "\n".join(ELEMENT_PREFIX + line for line in text.splitlines())


def write_json_array(stream: IO[bytes], pages: Iterable[Sequence[BaseDocument]]) -> int:
    """
    The documents of every page as one JSON array (`[]` for none), written
    as they come; how many there were.
    """

    count: int = 0
    stream.write(b"[")
    for page in pages:
        for document in page:
            separator: str = "\n" if count == 0 else ",\n"
            stream.write((separator + document_json(document)).encode("utf-8"))
            count += 1

    stream.write(b"\n]\n" if count else b"]\n")
    return count


def write_csv_table(
    stream: IO[bytes], header: Sequence[str], pages: Iterable[Sequence[CsvRow]]
) -> int:
    """
    A table as a spreadsheet opens it (`csv_writing`: BOM, CRLF, formulas
    defused), its rows written as their pages come; how many rows.
    """

    stream.write((UTF8_BOM + csv_line(header)).encode("utf-8"))
    count: int = 0
    for page in pages:
        for row in page:
            stream.write(csv_line([str(cell) for cell in row.cells]).encode("utf-8"))
            count += 1

    return count
