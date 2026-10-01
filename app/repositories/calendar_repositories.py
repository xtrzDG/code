from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.operations import (
    CalendarAuthorizationStateRepoContract,
    CalendarConnectionRepoContract,
    CalendarEventLinkRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import CalendarAuthorizationStateHash
from app.schemas.typings.businesses.prefixed_id import BusinessId


class CalendarConnectionRepository(CalendarConnectionRepoContract):
    """Stores one calendar connection per business, keyed by the business id."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[CalendarConnectionDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            CalendarConnectionDocument
        ] = collection

    def save(self, connection: CalendarConnectionDocument) -> None:
        self._collection.upsert(str(connection.business_id), connection)

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> CalendarConnectionDocument | None:
        connection: CalendarConnectionDocument | None = self._collection.get(
            str(business_id)
        )
        if connection is None or connection.business_id != business_id:
            return None

        return connection

    def delete_by_business(self, business_id: BusinessId) -> None:
        self._collection.delete(str(business_id))


class CalendarAuthorizationStateRepository(CalendarAuthorizationStateRepoContract):
    """Pending OAuth authorizations, keyed by the hash of their state."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[
            CalendarAuthorizationStateDocument
        ],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            CalendarAuthorizationStateDocument
        ] = collection

    def save(self, state: CalendarAuthorizationStateDocument) -> None:
        self._collection.upsert(str(state.state_hash), state)

    def find_by_state_hash(
        self,
        state_hash: CalendarAuthorizationStateHash,
    ) -> CalendarAuthorizationStateDocument | None:
        return self._collection.get(str(state_hash))


class CalendarEventLinkRepository(
    BusinessScopedRepository[CalendarEventLinkDocument],
    CalendarEventLinkRepoContract,
):
    """Booking-to-event links, keyed by the booking id."""

    def save(self, link: CalendarEventLinkDocument) -> None:
        self._store(str(link.booking_id), link)

    def find_by_booking(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> CalendarEventLinkDocument | None:
        return self._load(business_id, str(booking_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[CalendarEventLinkDocument]:
        return self._list(business_id)

    def delete_by_booking(self, business_id: BusinessId, booking_id: BookingId) -> None:
        self._remove(business_id, str(booking_id))
