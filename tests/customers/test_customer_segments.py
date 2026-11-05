"""
Saved segments: the owner's groups of customers by tag, last visit,
booking count and VIP flag, never holding blocked, erased or test-chat
customers; their members page by last activity.
"""

import pytest
from pydantic import ValidationError
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.customers.customer_segments import (
    SegmentListQuery,
    SegmentQuery,
    SegmentRequest,
    UpdateSegmentCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.contacts.constrained_strings import SegmentName
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import PageSize
from app.use_cases.contacts.segments.segment_support import MAX_SEGMENTS
from tests.customers.customer_bed import names_of, rules
from tests.customers.segment_bed import SegmentBed


def add_customer(
    bed: SegmentBed, name: str, *tags: str, is_tester: bool = False
) -> ContactDocument:
    """A customer active after every one before (a tester: of the test chat)."""

    repo = bed.customers.testbed.contact_repo
    business_id = bed.customers.business.id
    latest: int = max(
        int(contact.last_seen_at or 0) for contact in repo.list_by_business(business_id)
    )
    contact = ContactDocument(
        business_id=business_id,
        name=ContactName(name),
        last_seen_at=Microseconds(latest + 1_000_000),
        channel_identities=(
            [
                ChannelIdentity(
                    channel=ChannelKind.OWNER_TEST,
                    channel_user_id=ChannelUserId(f"owner:{name}"),
                )
            ]
            if is_tester
            else []
        ),
    )
    repo.save(contact)
    if tags:
        bed.tag(contact.id, *tags)
    return contact


def test_the_owner_saves_renames_and_deletes_a_segment() -> None:
    bed = SegmentBed()
    business_id = bed.customers.business.id
    bed.tag(bed.customers.giorgi.contact.id, "regular")
    first = bed.create("Regulars", rules(min_bookings=2))
    second = bed.create("Not back", rules(last_visit_days_ago=60, tag="regular"))

    renamed = bed.update_segment.run(
        UpdateSegmentCommand(
            user_id=bed.owner_id,
            business_id=business_id,
            segment_id=first.id,
            request=SegmentRequest(
                name=SegmentName("Loyal guests"), rules=rules(min_bookings=3)
            ),
        )
    )
    bed.delete_segment.run(
        SegmentQuery(
            user_id=bed.owner_id, business_id=business_id, segment_id=second.id
        )
    )
    listed = bed.list_segments.run(
        SegmentListQuery(user_id=bed.owner_id, business_id=business_id)
    )

    assert (str(renamed.name), renamed.rules.min_bookings) == ("Loyal guests", 3)
    assert [item.id for item in listed.items] == [first.id]
    assert [str(tag) for tag in listed.known_tags] == ["regular"]
    entries = bed.customers.testbed.audit_log_repo.list_by_business(business_id)
    assert [
        (entry.action, entry.entity_id)
        for entry in entries
        if entry.entity == "customer_segment"
    ] == [
        (AuditAction.CREATE, str(first.id)),
        (AuditAction.CREATE, str(second.id)),
        (AuditAction.UPDATE, str(first.id)),
        (AuditAction.DELETE, str(second.id)),
    ]
    with pytest.raises(NotFoundError):
        bed.members(second.id)


def test_segments_are_the_owners_and_stay_in_their_business() -> None:
    bed = SegmentBed()
    segment = bed.create("Regulars", rules(min_bookings=2))

    with pytest.raises(AccessDeniedError):
        bed.create("Mine", rules(), user_id=bed.staff_id)
    with pytest.raises(AccessDeniedError):
        bed.list_segments.run(
            SegmentListQuery(
                user_id=bed.staff_id, business_id=bed.customers.business.id
            )
        )
    with pytest.raises(NotFoundError):
        bed.members(CustomerSegmentId())
    assert bed.members(segment.id).items == []


def test_a_business_keeps_at_most_fifty_segments() -> None:
    bed = SegmentBed()
    for index in range(MAX_SEGMENTS):
        bed.create(f"Segment {index}", rules())

    with pytest.raises(ConflictError):
        bed.create("One too many", rules())


def test_rules_with_more_bookings_than_allowed_are_refused() -> None:
    with pytest.raises(ValidationError):
        rules(min_bookings=3, max_bookings=2)
    with pytest.raises(ValidationError):
        rules(last_visit_days_ago=0)


def test_a_tag_segment_holds_the_tagged_customers_in_any_case() -> None:
    bed = SegmentBed()
    bed.tag(bed.customers.giorgi.contact.id, "Regular")
    add_customer(bed, "Ana", "regular")
    add_customer(bed, "Levan", "wholesale")

    segment = bed.create("Regulars", rules(tag="REGULAR"))

    assert names_of(bed.members(segment.id).items) == ["Ana", "Giorgi"]


def test_customers_not_back_for_n_days() -> None:
    bed = SegmentBed()
    giorgi = bed.customers.giorgi.contact
    nino = bed.customers.nino.contact
    bed.add_booking(giorgi.id, days_ago=40)
    bed.add_booking(nino.id, days_ago=40)
    bed.add_booking(nino.id, days_ago=3)
    never_visited = add_customer(bed, "Ana")
    bed.add_booking(never_visited.id, days_ago=50, status=BookingStatus.CANCELLED)

    segment = bed.create("Not back in 30 days", rules(last_visit_days_ago=30))

    assert names_of(bed.members(segment.id).items) == ["Giorgi"]


def test_booking_count_rules() -> None:
    bed = SegmentBed()
    giorgi = bed.customers.giorgi.contact
    bed.add_booking(giorgi.id, days_ago=40)
    bed.add_booking(giorgi.id, days_ago=3)
    add_customer(bed, "Ana")

    many = bed.create("Three or more", rules(min_bookings=3))
    few = bed.create("At most one", rules(max_bookings=1))
    none = bed.create("Never booked", rules(max_bookings=0))

    assert names_of(bed.members(many.id).items) == ["Giorgi"]
    assert names_of(bed.members(few.id).items) == ["Ana", "Nino"]
    assert names_of(bed.members(none.id).items) == ["Ana"]


def test_vip_segments_and_left_out_customers() -> None:
    bed = SegmentBed()
    giorgi = bed.customers.giorgi.contact
    nino = bed.customers.nino.contact
    bed.tag(giorgi.id, is_vip=True)
    bed.tag(nino.id, is_vip=True)
    ana = add_customer(bed, "Ana")
    bed.tag(ana.id, is_vip=True)
    tester = add_customer(bed, "Tester", is_tester=True)
    bed.tag(tester.id, is_vip=True)
    segment = bed.create("VIPs", rules(vip_only=True))
    everyone = bed.create("Everyone", rules())
    assert names_of(bed.members(segment.id).items) == ["Ana", "Nino", "Giorgi"]

    bed.block(nino.id)
    bed.customers.testbed.contact_repo.save(
        ContactDocument(
            id=ana.id,
            business_id=ana.business_id,
            erased_at=bed.customers.testbed.clock.now_microseconds(),
        )
    )

    assert names_of(bed.members(segment.id).items) == ["Giorgi"]
    assert names_of(bed.members(everyone.id).items) == ["Giorgi"]


def test_members_page_by_last_activity_with_a_cursor() -> None:
    bed = SegmentBed()
    for name in ("Ana", "Levan", "Mariam", "Tamar", "Zura"):
        add_customer(bed, name, "terrace")
    segment = bed.create("Terrace", rules(tag="terrace"))

    first = bed.members(segment.id, PageRequest(size=PageSize(2)))
    second = bed.members(
        segment.id, PageRequest(size=PageSize(2), cursor=first.next_cursor)
    )
    third = bed.members(
        segment.id, PageRequest(size=PageSize(2), cursor=second.next_cursor)
    )

    assert names_of(first.items) == ["Zura", "Tamar"]
    assert names_of(second.items) == ["Mariam", "Levan"]
    assert (names_of(third.items), third.next_cursor) == (["Ana"], None)
    entry = bed.customers.testbed.audit_log_repo.list_by_business(
        bed.customers.business.id
    )[-1]
    assert (entry.action, entry.entity) == (AuditAction.VIEW, "contact")


def test_the_preview_counts_members_and_shows_a_few() -> None:
    bed = SegmentBed()
    for index in range(7):
        add_customer(bed, f"Guest {index}", "terrace")

    preview = bed.preview(rules(tag="terrace"))
    nobody = bed.preview(rules(tag="wholesale"))

    assert (preview.member_count, preview.is_count_exact) == (7, True)
    assert names_of(preview.sample) == [f"Guest {index}" for index in (6, 5, 4, 3, 2)]
    assert (nobody.member_count, nobody.sample) == (0, [])
