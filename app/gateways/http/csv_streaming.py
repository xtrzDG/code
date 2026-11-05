"""
A CSV export streamed to the browser a page at a time: the byte order
mark and the headings first, then each page of rows as it is read, so the
response never holds the table (100 000 rows cost one page of memory).
"""

from collections.abc import Callable, Iterator

from app.schemas.dto.privacy.csv_exports import CsvExportHeader, CsvExportPage
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.privacy.csv_writing import UTF8_BOM, csv_line

ENCODING: str = "utf-8"

type ReadCsvPage = Callable[[PageCursor | None], CsvExportPage]


def stream_csv(header: CsvExportHeader, read_page: ReadCsvPage) -> Iterator[bytes]:
    """The file's chunks: BOM and headings, then one chunk per page of rows."""

    yield (UTF8_BOM + csv_line([str(title) for title in header.columns])).encode(
        ENCODING
    )
    cursor: PageCursor | None = None
    while True:
        page: CsvExportPage = read_page(cursor)
        if page.rows:
            yield "".join(
                csv_line([str(cell) for cell in row.cells]) for row in page.rows
            ).encode(ENCODING)

        if page.next_cursor is None:
            return

        cursor = page.next_cursor


def attachment_disposition(file_name: str) -> str:
    """Content-Disposition of a download (the name is lowercase ASCII)."""

    return f'attachment; filename="{file_name}"'
