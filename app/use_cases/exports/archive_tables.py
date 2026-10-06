"""
The cabinet's tables in a full export: the same rows as their downloads
(`ReadCsvExportPageUseCase`'s readers, default filters), read one keyset
page at a time.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.schemas.constants.privacy import CsvExportKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.privacy.csv_exports import (
    CsvExportPage,
    CsvExportPageQuery,
    CsvRow,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.exports.read_csv_export_page_use_case import (
    PAGE_SIZES,
    CsvRowReader,
)


@dataclass(frozen=True)
class ArchiveTables:
    """The row readers of the tables, by table."""

    readers: Mapping[CsvExportKind, CsvRowReader]

    def pages(
        self,
        kind: CsvExportKind,
        business: BusinessDocument,
        zone: ZoneInfo,
        viewer: UserId,
    ) -> Iterator[list[CsvRow]]:
        """Every row of one table, a page at a time (`viewer` reads all views)."""

        cursor: PageCursor | None = None
        while True:
            page: CsvExportPage = self.readers[kind].read(
                business,
                zone,
                CsvExportPageQuery(
                    user_id=viewer, business_id=business.id, kind=kind, cursor=cursor
                ),
                PageRequest(size=PAGE_SIZES[kind], cursor=cursor),
            )
            yield page.rows
            if page.next_cursor is None:
                return

            cursor = page.next_cursor
