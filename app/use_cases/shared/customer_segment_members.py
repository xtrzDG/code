"""
The members of a segment, found by walking the customer list.

A segment is stored as rules, never as a member list, so it is never
stale. Its members come from a walk of the customers most recently active
first in keyset batches: the tag and VIP rules narrow the walk in the
database (indexed tag lookup, VIP column); booking counts and visits are
counted by the database for each batch (one aggregation each); blocked,
erased and test-only contacts are left out. One read looks at most at
`scan_limit` customers; when it stops there with room left, its cursor
points after the last one it looked at, so the next read goes on from
there (a page may then hold fewer members than asked, even none). Campaigns
read the same walk (W17).
"""

from dataclasses import dataclass, field
from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.contact_activity_repositories import (
    ContactActivityRepoContract,
)
from app.contracts.repositories.customer_repositories import (
    CustomerCardRepoContract,
    CustomerHistoryRepoContract,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.customer_segments import SegmentRules
from app.schemas.dto.contacts import ContactActivityTotals
from app.schemas.dto.customers.customer_records import ContactVisits, CustomerPageFilter
from app.schemas.dto.paging import KeysetPosition, KeysetSlice, PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.paging.cursor_paging import encode_page_cursor
from app.utilities.paging.keyset_paging import read_slice, single_value_position

SEGMENT_BATCH: int = 200
# Customers one page of members (or one CSV page) looks at, at most.
MEMBER_SCAN_LIMIT: int = 2_000
MICROSECONDS_PER_DAY: int = int(timedelta(days=1).total_seconds()) * 1_000_000


@dataclass(frozen=True)
class SegmentReaders:
    """The repositories a walk reads."""

    card_repo: CustomerCardRepoContract
    activity_repo: ContactActivityRepoContract
    history_repo: CustomerHistoryRepoContract


@dataclass(frozen=True)
class SegmentScan:
    """The members one read found, how many it looked at, where to go on."""

    members: list[ContactDocument] = field(default_factory=list[ContactDocument])
    scanned: int = 0
    next_cursor: PageCursor | None = None


def scan_segment(
    readers: SegmentReaders,
    business_id: BusinessId,
    rules: SegmentRules,
    now: Microseconds,
    page: PageRequest,
    scan_limit: int = MEMBER_SCAN_LIMIT,
) -> SegmentScan:
    """
    Up to `page.size` members after the page's cursor (one more is looked
    for, so a full last page has no cursor).

    Raises:
        ValidationFailedError: the cursor is broken.
    """

    size: int = int(page.size)
    page_filter = CustomerPageFilter(tag=rules.tag, vip_only=rules.vip_only)
    after: KeysetPosition | None = read_slice(page).after
    members: list[ContactDocument] = []
    scanned: int = 0
    while scanned < scan_limit:
        batch: list[ContactDocument] = readers.card_repo.page_customers(
            business_id,
            KeysetSlice(after=after, limit=KeysetReadLimit(SEGMENT_BATCH)),
            page_filter,
        )
        matching: set[ContactId] = matching_ids(readers, business_id, rules, now, batch)
        for contact in batch:
            scanned += 1
            if contact.id not in matching:
                continue

            members.append(contact)
            if len(members) > size:
                return SegmentScan(
                    members=members[:size],
                    scanned=scanned,
                    next_cursor=cursor_after(members[size - 1]),
                )

        if len(batch) < SEGMENT_BATCH:
            return SegmentScan(members=members, scanned=scanned)

        after = position_of(batch[-1])

    return SegmentScan(
        members=members,
        scanned=scanned,
        next_cursor=None if after is None else encode_position(after),
    )


def matching_ids(
    readers: SegmentReaders,
    business_id: BusinessId,
    rules: SegmentRules,
    now: Microseconds,
    batch: list[ContactDocument],
) -> set[ContactId]:
    """The customers of a batch the rules hold for (two aggregations at most)."""

    candidates: list[ContactDocument] = [
        contact
        for contact in batch
        if contact.erased_at is None
        and contact.block is None
        and not contact.is_test_only
    ]
    ids: list[ContactId] = [contact.id for contact in candidates]
    has_count_rule: bool = (
        rules.min_bookings is not None or rules.max_bookings is not None
    )
    totals: dict[ContactId, ContactActivityTotals] = (
        readers.activity_repo.count_for_contacts(business_id, ids)
        if has_count_rule and ids
        else {}
    )
    visits: dict[ContactId, ContactVisits] = (
        readers.history_repo.visits_for_contacts(business_id, ids, now)
        if rules.last_visit_days_ago is not None and ids
        else {}
    )
    return {
        contact.id
        for contact in candidates
        if holds(rules, totals.get(contact.id), visits.get(contact.id), now)
    }


def holds(
    rules: SegmentRules,
    totals: ContactActivityTotals | None,
    visits: ContactVisits | None,
    now: Microseconds,
) -> bool:
    """Whether the count and visit rules hold (tag and VIP held in the walk)."""

    booking_count: int = 0 if totals is None else int(totals.booking_count)
    if rules.min_bookings is not None and booking_count < int(rules.min_bookings):
        return False

    if rules.max_bookings is not None and booking_count > int(rules.max_bookings):
        return False

    if rules.last_visit_days_ago is None:
        return True

    if visits is None or visits.last_visit_at is None:
        return False

    cutoff: int = int(now) - int(rules.last_visit_days_ago) * MICROSECONDS_PER_DAY
    return int(visits.last_visit_at) < cutoff


def position_of(contact: ContactDocument) -> KeysetPosition:
    return single_value_position(int(contact.last_seen_at or 0), str(contact.id))


def cursor_after(contact: ContactDocument) -> PageCursor:
    return encode_page_cursor(int(contact.last_seen_at or 0), str(contact.id))


def encode_position(position: KeysetPosition) -> PageCursor:
    return encode_page_cursor(int(position.sort_values[0]), str(position.item_key))
