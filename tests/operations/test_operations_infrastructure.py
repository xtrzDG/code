"""Lock registry, staff broadcast and calendar repositories."""

import threading
import time

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.staff.manager_broadcast_facilitator import (
    ManagerBroadcastFacilitator,
)
from app.registries.locks.business_lock_registry import BusinessLockRegistry
from app.repositories.calendar_repositories import (
    CalendarConnectionRepository,
    CalendarEventLinkRepository,
)
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.calendar import (
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.operations import StaffMessage
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import CalendarEventId, ExternalCalendarId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.builders import manager
from tests.operations.fakes import RecordingManagerNotifier


def test_lock_registry_serializes_one_business_but_not_others() -> None:
    registry = BusinessLockRegistry()
    first, second = BusinessId(), BusinessId()
    events: list[str] = []

    def hold_first() -> None:
        with registry.lock_for(first):
            events.append("first-start")
            time.sleep(0.05)
            events.append("first-end")

    holder = threading.Thread(target=hold_first)
    holder.start()
    while "first-start" not in events:
        time.sleep(0.001)

    with registry.lock_for(second):
        events.append("second")

    with registry.lock_for(first):
        events.append("first-again")

    holder.join()

    assert events == ["first-start", "second", "first-end", "first-again"]
    assert registry.lock_for(first) is registry.lock_for(first)


def test_broadcast_counts_deliveries_and_survives_failures() -> None:
    notifier = RecordingManagerNotifier(
        failing_addresses=frozenset({"+995555000111"}),
        raising_addresses=frozenset({"boom@example.com"}),
    )
    broadcaster = ManagerBroadcastFacilitator(notifier)
    contacts = [
        manager("Nino", ManagerContactChannel.TELEGRAM, "4242", "ka"),
        manager("Boom", ManagerContactChannel.EMAIL, "boom@example.com", "en"),
        manager("Daniel", ManagerContactChannel.WHATSAPP, "+995555000111", "ru"),
        manager("Anna", ManagerContactChannel.SMS, "+995555000222", "en"),
    ]

    delivered = broadcaster.broadcast(
        [StaffMessage(contact=contact, text=MessageText("Hi")) for contact in contacts]
    )

    assert delivered == 2
    assert broadcaster.broadcast([]) == 0


def test_calendar_repositories_are_scoped_by_business() -> None:
    connections = CalendarConnectionRepository(
        InMemoryDocumentCollectionAdapter[CalendarConnectionDocument](
            CalendarConnectionDocument
        )
    )
    links = CalendarEventLinkRepository(
        InMemoryDocumentCollectionAdapter[CalendarEventLinkDocument](
            CalendarEventLinkDocument
        )
    )
    business, stranger = BusinessId(), BusinessId()
    booking_id = BookingId()
    connections.save(
        CalendarConnectionDocument(
            business_id=business,
            calendar_id=ExternalCalendarId("primary"),
            encrypted_refresh_token=EncryptedChannelSecret("enc:x"),
            connected_by=UserId(),
        )
    )
    links.save(
        CalendarEventLinkDocument(
            business_id=business,
            booking_id=booking_id,
            calendar_id=ExternalCalendarId("primary"),
            event_id=CalendarEventId("event1"),
        )
    )

    assert connections.get_by_business(business) is not None
    assert connections.get_by_business(stranger) is None
    assert links.find_by_booking(stranger, booking_id) is None
    links.delete_by_booking(stranger, booking_id)
    assert links.find_by_booking(business, booking_id) is not None
    links.delete_by_booking(business, booking_id)
    assert links.list_by_business(business) == []
    connections.delete_by_business(business)
    assert connections.get_by_business(business) is None
