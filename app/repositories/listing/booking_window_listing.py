"""The bookings of a calendar window, a keyset page at a time."""

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_other_than
from app.repositories.listing.booking_listing import (
    ENDS_AT_FIELD,
    STARTS_AT_FIELD,
    STATUS_FIELD,
    sandbox_exclusion,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.booking_grid import BookingWindow
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.integers import DocumentFieldInteger


class BookingWindowListing(BusinessScopedRepository[BookingDocument]):
    """Pages of the bookings a calendar window shows (cancelled ones never)."""

    def page_in_window(
        self, business_id: BusinessId, window: BookingWindow, page: KeysetSlice
    ) -> list[BookingDocument]:
        return self._page_in_business(
            business_id,
            (STARTS_AT_FIELD,),
            page,
            DocumentFilter(
                excluding=(
                    field_other_than(STATUS_FIELD, BookingStatus.CANCELLED),
                    *sandbox_exclusion(window.include_sandbox),
                ),
                ranges=(
                    DocumentFieldRange(
                        field=STARTS_AT_FIELD,
                        lower=DocumentFieldInteger(int(window.starts_from)),
                        upper=DocumentFieldInteger(int(window.starts_before)),
                    ),
                    DocumentFieldRange(
                        field=ENDS_AT_FIELD,
                        lower=DocumentFieldInteger(int(window.ends_after) + 1),
                        upper=(
                            None
                            if window.ends_by is None
                            else DocumentFieldInteger(int(window.ends_by) + 1)
                        ),
                    ),
                ),
            ),
            is_descending=False,
        )
