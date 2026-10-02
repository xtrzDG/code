"""Lock registry and calendar repositories."""

import threading
import time

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.locks.business_lock_registry import BusinessLockRegistry
from app.repositories.calendar_repositories import (
    CalendarConnectionRepository,
    CalendarEventLinkRepository,
)
from app.schemas.domain.calendar import (
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import CalendarEventId, ExternalCalendarId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.users.prefixed_id import UserId


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
