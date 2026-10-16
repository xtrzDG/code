"""What the customers repositories read: list filters and per-customer totals."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.contacts.booleans import IsBlockedOnlyFilter, IsVipOnlyFilter
from app.schemas.typings.contacts.constrained_integers import ContactVisitCount
from app.schemas.typings.contacts.constrained_strings import CustomerTag


class CustomerPageFilter(ImmutableDTO):
    """
    Which customers a page of the list holds: those with `tag` (indexed),
    only VIPs, only blocked ones. A customer can be VIP or blocked only
    since the card exists (1140), so these filters need no backfill.
    """

    tag: CustomerTag | None = None
    vip_only: IsVipOnlyFilter = False
    blocked_only: IsBlockedOnlyFilter = False


class ContactVisits(ImmutableDTO):
    """
    A customer's visits, counted by the database: bookings that started
    before the moment asked about and were confirmed or completed (test
    chats left out), and when the latest of them started.
    """

    visit_count: ContactVisitCount = ContactVisitCount(0)
    last_visit_at: Microseconds | None = None
