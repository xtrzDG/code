from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.deposit_repositories import BookingOutcomeRepoContract
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import without_sandbox
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.deposits.deposit_counts import BookingOutcomeRow
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.constrained_integers import DepositOutcomeCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
DEPOSIT_STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("deposit_status")
STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")


class BookingOutcomeRepository(
    BusinessScopedRepository[BookingDocument],
    BookingOutcomeRepoContract,
):
    """
    The deposits report's comparison over the bookings collection: the
    bookings that started in a window per status and deposit state,
    grouped by the database (the start-time index reads the window, the
    trigger-filled deposit status column of 1190 groups it).
    """

    def __init__(
        self, booking_collection: DocumentCollectionAdapterContract[BookingDocument]
    ) -> None:
        super().__init__(booking_collection)

    def count_outcomes(
        self,
        business_id: BusinessId,
        starts_from: BookingSearchBoundSeconds,
        starts_before: BookingSearchBoundSeconds,
    ) -> list[BookingOutcomeRow]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    excluding=(without_sandbox(),),
                    ranges=(
                        DocumentFieldRange(
                            field=STARTS_AT_FIELD,
                            lower=DocumentFieldInteger(int(starts_from)),
                            upper=DocumentFieldInteger(int(starts_before)),
                        ),
                    ),
                ),
                group_by=(STATUS_FIELD, DEPOSIT_STATUS_FIELD),
            ),
        )
        return [
            BookingOutcomeRow(
                status=status,
                deposit_status=parse_choice(DepositStatus, group.values[1]),
                count=DepositOutcomeCount(int(group.count)),
            )
            for group in groups
            if (status := parse_choice(BookingStatus, group.values[0])) is not None
        ]
