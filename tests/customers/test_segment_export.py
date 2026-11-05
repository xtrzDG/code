"""
A segment's members as CSV for a campaign elsewhere: owners only, after a
recent sign-in, audited, headings in the owner's language, streamed in
keyset pages; and the walk behind it, bounded per read.
"""

import csv
import io

import pytest
from typed_time_provider import Microseconds

from app.gateways.http.csv_streaming import stream_csv
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.customer_segments import SegmentRules
from app.schemas.dto.customers.customer_segments import StartSegmentExportCommand
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.contacts.prefixed_id import ContactId, CustomerSegmentId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import PageSize
from app.use_cases.shared.customer_segment_members import SegmentScan, scan_segment
from tests.customers.customer_bed import RefuseStepUp, rules
from tests.customers.segment_bed import SegmentBed


def read_csv(
    bed: SegmentBed, segment_id: CustomerSegmentId, language: str = "en"
) -> list[list[str]]:
    header = bed.export_header(segment_id, language)
    chunks = stream_csv(header, lambda cursor: bed.export_page(segment_id, cursor))
    text = b"".join(chunks).decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def add_regulars(bed: SegmentBed, count: int) -> list[ContactId]:
    repo = bed.customers.testbed.contact_repo
    business_id = bed.customers.business.id
    latest = max(
        int(contact.last_seen_at or 0) for contact in repo.list_by_business(business_id)
    )
    ids: list[ContactId] = []
    for index in range(count):
        contact = ContactDocument(
            business_id=business_id,
            name=ContactName(f"Guest {index:03d}"),
            last_seen_at=Microseconds(latest + (index + 1) * 1_000_000),
        )
        repo.save(contact)
        bed.tag(contact.id, "regular")
        ids.append(contact.id)
    return ids


def test_the_owner_downloads_a_segment_as_csv() -> None:
    bed = SegmentBed()
    giorgi = bed.customers.giorgi.contact
    bed.tag(giorgi.id, "regular", "terrace", is_vip=True)
    segment = bed.create("Regulars", rules(tag="regular"))

    rows = read_csv(bed, segment.id, language="ru")

    assert rows[0][:3] == ["ID клиента", "Имя", "Телефон"]
    assert len(rows[0]) == 11
    # (a leading "+" is defused for spreadsheets)
    assert rows[1][:3] == [str(giorgi.id), "Giorgi", "'+995577123456"]
    assert rows[1][6] == "regular; terrace"
    header = bed.export_header(segment.id)
    assert str(header.file_name).startswith("segment-")
    assert str(header.file_name).endswith(".csv")
    exports = [
        entry
        for entry in bed.customers.testbed.audit_log_repo.list_by_business(
            giorgi.business_id
        )
        if entry.action is AuditAction.EXPORT
    ]
    assert [(entry.entity, entry.entity_id) for entry in exports] == [
        ("customer_segment", str(segment.id))
    ] * 2


def test_a_long_segment_streams_in_pages() -> None:
    bed = SegmentBed()
    ids = add_regulars(bed, 230)
    segment = bed.create("Regulars", rules(tag="regular"))

    rows = read_csv(bed, segment.id)

    assert [row[0] for row in rows[1:]] == [str(item) for item in reversed(ids)]


def test_the_export_needs_a_recent_sign_in_and_the_owner() -> None:
    owner_bed = SegmentBed()
    segment = owner_bed.create("Regulars", rules())
    bed = SegmentBed(owner_bed.customers, step_up=RefuseStepUp())

    with pytest.raises(StepUpRequiredError):
        bed.export_header(segment.id)
    with pytest.raises(AccessDeniedError):
        bed.start_export.run(
            StartSegmentExportCommand(
                user_id=bed.staff_id,
                business_id=bed.customers.business.id,
                segment_id=segment.id,
                language=LanguageTag("en"),
            )
        )
    assert not any(
        entry.action is AuditAction.EXPORT
        for entry in bed.customers.testbed.audit_log_repo.list_by_business(
            bed.customers.business.id
        )
    )


def test_one_read_looks_at_a_bounded_number_of_customers_and_goes_on() -> None:
    bed = SegmentBed()
    regulars = add_regulars(bed, 3)
    # The regulars are the most recent; the rule holds only for the oldest.
    bed.tag(regulars[0], "first")
    segment_rules = SegmentRules(tag=CustomerTag("first"))
    business_id = bed.customers.business.id
    now = bed.customers.testbed.clock.now_microseconds()

    everyone = SegmentRules()
    stopped: SegmentScan = scan_segment(
        bed.readers, business_id, everyone, now, PageRequest(size=PageSize(10)), 2
    )
    found: SegmentScan = scan_segment(
        bed.readers, business_id, segment_rules, now, PageRequest(size=PageSize(1))
    )

    assert (len(stopped.members), stopped.scanned) == (2, 2)
    assert stopped.next_cursor is not None
    rest = scan_segment(
        bed.readers,
        business_id,
        everyone,
        now,
        PageRequest(size=PageSize(10), cursor=stopped.next_cursor),
    )
    assert [member.id for member in stopped.members + rest.members][:3] == list(
        reversed(regulars)
    )
    assert len(stopped.members + rest.members) == 5
    assert ([member.id for member in found.members], found.next_cursor) == (
        [regulars[0]],
        None,
    )
