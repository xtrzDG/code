"""The bookings of a calendar window (the cabinet's day, week and nights grids)."""

from typing import Protocol

from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.booking_grid import BookingWindow
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BookingWindowListingContract(Protocol):
    def page_in_window(
        self, business_id: BusinessId, window: BookingWindow, page: KeysetSlice
    ) -> list[BookingDocument]:
        """
        One keyset page of the bookings of the window (`BookingWindow`),
        by start time, ties in write order: an index range scan bounded on
        both sides of the start, filtered by the end.
        """
        raise NotImplementedError
