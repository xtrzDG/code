"""
CSV exports of the cabinet's tables: owners only, audited once, escaped
for spreadsheets, a byte order mark first, the lists' filters, and no row
of an erased customer.
"""

import csv
import io

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import CsvExportKind
from app.schemas.dto.privacy.csv_exports import CsvExportFilters
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.utilities.privacy.csv_writing import UTF8_BOM, csv_line, escape_cell
from tests.compliance.two_tenants import command, seed_two_tenants
from tests.privacy.csv_export_bed import CsvExportBed


def read_rows(text: str) -> list[list[str]]:
    assert text.startswith(UTF8_BOM)
    return list(csv.reader(io.StringIO(text.removeprefix(UTF8_BOM))))


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ('=HYPERLINK("http://x")', '\'=HYPERLINK("http://x")'),
        ("+995599123456", "'+995599123456"),
        ("-2+3", "'-2+3"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tcmd", "'\tcmd"),
        ("\rcmd", "'\rcmd"),
        ("  =1+1", "'  =1+1"),
        ("Nino", "Nino"),
        ("a=b", "a=b"),
        ("", ""),
    ],
)
def test_a_value_a_spreadsheet_would_run_is_kept_as_text(
    value: str, written: str
) -> None:
    assert escape_cell(value) == written


def test_a_line_quotes_commas_quotes_and_line_breaks() -> None:
    line = csv_line(['Table "4", window', "two\nlines", "=1"])

    assert line == '"Table ""4"", window","two\nlines",\'=1\r\n'
    assert next(csv.reader(io.StringIO(line))) == [
        'Table "4", window',
        "two\nlines",
        "'=1",
    ]


def test_the_owner_downloads_bookings_with_a_bom_headings_and_rows() -> None:
    tenants = seed_two_tenants()
    bed = CsvExportBed(tenants)

    rows = read_rows(bed.csv(CsvExportKind.BOOKINGS))

    assert rows[0][:3] == ["Booking ID", "Date", "Time"]
    ids = {row[0] for row in rows[1:]}
    assert str(tenants.visitor.booking.id) in ids
    assert str(tenants.neighbour.booking.id) in ids
    assert str(tenants.foreign_visitor.booking.id) not in ids
    giorgi = next(row for row in rows if row[0] == str(tenants.visitor.booking.id))
    assert "Giorgi" in giorgi
    assert "'+995577123456" in giorgi


def test_the_export_is_audited_once_however_many_pages() -> None:
    tenants = seed_two_tenants()
    bed = CsvExportBed(tenants)

    header = bed.header(CsvExportKind.CONTACTS)
    bed.page(CsvExportKind.CONTACTS)
    bed.page(CsvExportKind.CONTACTS)

    assert str(header.file_name).startswith("contacts-")
    exports = [
        entry
        for entry in tenants.testbed.audit_log_repo.list_by_business(
            tenants.business.id
        )
        if entry.action is AuditAction.EXPORT
    ]
    assert [(str(e.entity), str(e.entity_id)) for e in exports] == [("contact", "csv")]
    assert exports[0].actor_id == tenants.owner_id
    assert str(exports[0].ip_address) == "192.0.2.10"


def test_staff_may_not_export_or_read_pages() -> None:
    tenants = seed_two_tenants()
    bed = CsvExportBed(tenants)

    with pytest.raises(AccessDeniedError):
        bed.header(CsvExportKind.BOOKINGS, user_id=tenants.staff_id)
    with pytest.raises(AccessDeniedError):
        bed.page(CsvExportKind.BOOKINGS, user_id=tenants.staff_id)

    assert not any(
        entry.action is AuditAction.EXPORT
        for entry in tenants.testbed.audit_log_repo.list_by_business(
            tenants.business.id
        )
    )


@pytest.mark.parametrize("kind", list(CsvExportKind))
def test_an_erased_customer_is_in_no_table(kind: CsvExportKind) -> None:
    tenants = seed_two_tenants()
    bed = CsvExportBed(tenants)
    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    text = bed.csv(kind)

    for erased in (
        tenants.visitor.contact.id,
        tenants.visitor.booking.id,
        tenants.visitor.lead.id,
        tenants.visitor.chat_conversation.id,
    ):
        if kind is not CsvExportKind.AUDIT_LOG:
            assert str(erased) not in text
    assert "Giorgi" not in text
    assert "577123456" not in text


def test_the_neighbour_stays_in_every_customer_table() -> None:
    tenants = seed_two_tenants()
    bed = CsvExportBed(tenants)
    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )

    assert str(tenants.neighbour.contact.id) in bed.csv(CsvExportKind.CONTACTS)
    assert str(tenants.neighbour.lead.id) in bed.csv(CsvExportKind.LEADS)
    conversations = read_rows(bed.csv(CsvExportKind.CONVERSATIONS))
    texts = [row[-1] for row in conversations[1:]]
    assert "Hi, I am Nino" in texts


def test_the_lists_filters_apply() -> None:
    tenants = seed_two_tenants()
    bed = CsvExportBed(tenants)

    cancelled = bed.csv(
        CsvExportKind.BOOKINGS,
        CsvExportFilters(booking_status=BookingStatus.CANCELLED),
    )
    found = bed.csv(
        CsvExportKind.CONTACTS, CsvExportFilters(search=ContactSearchText("nin"))
    )
    exports_only = bed.csv(
        CsvExportKind.AUDIT_LOG, CsvExportFilters(action=AuditAction.EXPORT)
    )

    assert len(read_rows(cancelled)) == 1  # the headings only
    assert [row[1] for row in read_rows(found)[1:]] == ["Nino"]
    assert {row[1] for row in read_rows(exports_only)[1:]} == {"export"}


@pytest.mark.parametrize(
    ("language", "first_heading"),
    [("en", "Booking ID"), ("ru", "ID брони"), ("ka", "ჯავშნის ID")],
)
def test_headings_are_in_the_owners_language(language: str, first_heading: str) -> None:
    tenants = seed_two_tenants()

    header = CsvExportBed(tenants).header(CsvExportKind.BOOKINGS, language)

    assert str(header.columns[0]) == first_heading
    assert len(header.columns) == 17
