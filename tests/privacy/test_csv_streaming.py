"""
A big table streams: 100 000 audit entries leave as CSV a page at a time.
The log is generated as the pages are read, so the test also proves the
export never asks for more than one page ahead of what it has written.
"""

import csv
import io

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.gateways.http.csv_streaming import stream_csv
from app.repositories.compliance_repositories import AuditLogRepository
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.listing_filters import AuditLogFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.utilities.privacy.csv_writing import UTF8_BOM
from tests.compliance.two_tenants import seed_two_tenants
from tests.privacy.csv_export_bed import CsvExportBed

ENTRY_COUNT: int = 100_000
NEWEST: int = 1_800_000_000_000_000


class GeneratedAuditLog(AuditLogRepository):
    """A log of ENTRY_COUNT entries, newest first, made page by page."""

    def __init__(self) -> None:
        super().__init__(InMemoryDocumentCollectionAdapter(AuditLogEntryDocument))
        self.page_reads: int = 0
        self.largest_read: int = 0

    def page_by_business(
        self, business_id: BusinessId, window: KeysetSlice, log_filter: AuditLogFilter
    ) -> list[AuditLogEntryDocument]:
        self.page_reads += 1
        self.largest_read = max(self.largest_read, int(window.limit))
        start: int = (
            0 if window.after is None else NEWEST - int(window.after.sort_values[0]) + 1
        )
        return [
            AuditLogEntryDocument(
                business_id=business_id,
                action=AuditAction.VIEW,
                entity=AuditEntityName("booking"),
                created_at=Microseconds(NEWEST - index),
                updated_at=Microseconds(NEWEST - index),
            )
            for index in range(start, min(start + int(window.limit), ENTRY_COUNT))
        ]


def test_a_hundred_thousand_rows_stream_one_page_at_a_time() -> None:
    log = GeneratedAuditLog()
    bed = CsvExportBed(seed_two_tenants(), audit_log_repo=log)
    chunks = stream_csv(
        bed.header(CsvExportKind.AUDIT_LOG),
        lambda cursor: bed.page(CsvExportKind.AUDIT_LOG, cursor=cursor),
    )

    heading = next(chunks)
    assert heading.decode("utf-8").startswith(UTF8_BOM + "Time,")
    assert log.page_reads == 0  # nothing is read before the client asks
    first_rows = next(chunks)
    assert log.page_reads == 1
    row_count: int = first_rows.count(b"\r\n")
    largest_chunk: int = len(first_rows)
    for chunk in chunks:
        # One page read per chunk written: never more than one page ahead.
        assert log.page_reads * 200 >= row_count
        row_count += chunk.count(b"\r\n")
        largest_chunk = max(largest_chunk, len(chunk))

    assert row_count == ENTRY_COUNT
    assert log.page_reads == ENTRY_COUNT // 200
    assert log.largest_read == 201  # a page and one more to see the next
    assert largest_chunk < 64 * 1024
    last_line = first_rows.decode("utf-8").splitlines()[0]
    assert next(csv.reader(io.StringIO(last_line)))[1] == "view"
