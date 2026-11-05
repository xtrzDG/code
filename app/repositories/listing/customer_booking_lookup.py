"""A customer's own bookings by contact (migration 1184's index)."""

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    IS_SANDBOX_FIELD,
    field_among,
    of_business,
    without_sandbox,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.customer_bookings import ContactBookingLookup
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldExclusion,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")
ENDS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("ends_at")


class CustomerBookingLookup(BusinessScopedRepository[BookingDocument]):
    """
    The bookings of a few contacts that are not over yet, one indexed read
    over `(business_id, contact_id, ends_at)`; status and sandbox mode
    narrow those few rows, and the database orders them by start.
    """

    def list_for_contacts(
        self, business_id: BusinessId, lookup: ContactBookingLookup
    ) -> list[BookingDocument]:
        if not lookup.contact_ids or not lookup.statuses:
            return []

        among: list[DocumentFieldAmong] = [
            field_among(CONTACT_ID_FIELD, lookup.contact_ids),
            field_among(STATUS_FIELD, lookup.statuses),
        ]
        excluding: tuple[DocumentFieldExclusion, ...] = ()
        if lookup.is_sandbox:
            among.append(field_among(IS_SANDBOX_FIELD, (True,)))
        else:
            excluding = (without_sandbox(),)

        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(of_business(business_id),),
                    among=tuple(among),
                    excluding=excluding,
                    ranges=(
                        DocumentFieldRange(
                            field=ENDS_AT_FIELD,
                            lower=DocumentFieldInteger(int(lookup.ends_after) + 1),
                        ),
                    ),
                ),
                sort_fields=(STARTS_AT_FIELD,),
                is_descending=False,
                limit=lookup.limit,
            )
        )
