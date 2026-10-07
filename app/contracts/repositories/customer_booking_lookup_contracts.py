"""A customer's own bookings, read by their contacts through an index."""

from typing import Protocol

from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.customer_bookings import ContactBookingLookup
from app.schemas.typings.businesses.prefixed_id import BusinessId


class CustomerBookingLookupContract(Protocol):
    def list_for_contacts(
        self, business_id: BusinessId, lookup: ContactBookingLookup
    ) -> list[BookingDocument]:
        """
        The bookings of the lookup's contacts that it asks for, by start
        time (ties in write order), read through the contact and the end of
        each booking: the cost follows the customer's bookings, not the
        business's.
        """
        raise NotImplementedError
