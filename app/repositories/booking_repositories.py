from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories import BookingRepoContract, LeadRepoContract
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BookingRepository(BookingRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[BookingDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[BookingDocument] = (
            collection
        )

    def save(self, booking: BookingDocument) -> None:
        self._collection.upsert(str(booking.id), booking)

    def get(self, booking_id: BookingId) -> BookingDocument | None:
        return self._collection.get(str(booking_id))

    def list_by_business(self, business_id: BusinessId) -> list[BookingDocument]:
        bookings: list[BookingDocument] = [
            booking
            for booking in self._collection.list_all()
            if booking.business_id == business_id
        ]
        return sorted(bookings, key=lambda booking: booking.starts_at)


class LeadRepository(LeadRepoContract):
    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[LeadDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[LeadDocument] = collection

    def save(self, lead: LeadDocument) -> None:
        self._collection.upsert(str(lead.id), lead)

    def get(self, lead_id: LeadId) -> LeadDocument | None:
        return self._collection.get(str(lead_id))

    def list_by_business(self, business_id: BusinessId) -> list[LeadDocument]:
        leads: list[LeadDocument] = [
            lead
            for lead in self._collection.list_all()
            if lead.business_id == business_id
        ]
        return sorted(leads, key=lambda lead: lead.created_at, reverse=True)
