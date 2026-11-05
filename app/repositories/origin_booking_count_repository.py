from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.campaign_repositories import (
    OriginBookingCountRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_among,
    time_range,
    without_sandbox,
)
from app.schemas.constants.bookings import BookingOrigin, BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.growth.growth_counts import OriginBookingCount
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.value.constrained_integers import BookedValueMinor

ORIGIN_FIELD: DocumentFieldPath = DocumentFieldPath("origin")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
CURRENCY_CODE_FIELD: DocumentFieldPath = DocumentFieldPath("currency_code")
VALUE_FIELD: DocumentFieldPath = DocumentFieldPath("value_minor")


class OriginBookingCountRepository(
    BusinessScopedRepository[BookingDocument],
    OriginBookingCountRepoContract,
):
    """
    The value model's growth lines over the bookings collection: the
    bookings the waitlist and the campaigns brought, grouped by the
    database (the creation-time index reads the period, the trigger-filled
    origin column of 1151 narrows it).
    """

    def __init__(
        self, booking_collection: DocumentCollectionAdapterContract[BookingDocument]
    ) -> None:
        super().__init__(booking_collection)

    def count_by_origin(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[OriginBookingCount]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    among=(field_among(ORIGIN_FIELD, tuple(BookingOrigin)),),
                    excluding=(without_sandbox(),),
                    ranges=(
                        time_range(
                            CREATED_AT_FIELD, starting_at=start, ending_before=end
                        ),
                    ),
                ),
                group_by=(ORIGIN_FIELD, STATUS_FIELD, CURRENCY_CODE_FIELD),
                totals_of=(VALUE_FIELD,),
            ),
        )
        counts: list[OriginBookingCount] = []
        for group in groups:
            origin = parse_choice(BookingOrigin, group.values[0])
            status = parse_choice(BookingStatus, group.values[1])
            if origin is None or status is None:
                continue

            counts.append(
                OriginBookingCount(
                    origin=origin,
                    status=status,
                    currency_code=(
                        None
                        if group.values[2] is None
                        else CurrencyCode(group.values[2])
                    ),
                    count=PeriodItemCount(int(group.count)),
                    value_minor=BookedValueMinor(int(group.totals[0])),
                )
            )

        return counts
