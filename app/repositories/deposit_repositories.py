from typed_time_provider import Microseconds

from app.contracts.repositories.deposit_repositories import (
    DepositRequestChange,
    DepositRequestRepoContract,
    DepositSettingsChange,
    DepositSettingsRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    ascending,
    field_equals,
    time_range,
    without_sandbox,
)
from app.schemas.constants.deposits import DepositStatus
from app.schemas.domain.deposits import DepositRequestDocument, DepositSettingsDocument
from app.schemas.dto.deposits.deposit_counts import DepositSumRow
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.constrained_integers import (
    DepositRequestCount,
    DepositTotalMinor,
)
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.deposits.deposit_keys import deposit_settings_id_of

BOOKING_ID_FIELD: DocumentFieldPath = DocumentFieldPath("booking_id")
LEAD_ID_FIELD: DocumentFieldPath = DocumentFieldPath("lead_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
HOLD_EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("hold_expires_at")
REMINDER_DUE_AT_FIELD: DocumentFieldPath = DocumentFieldPath("reminder_due_at")
SETTLE_AFTER_FIELD: DocumentFieldPath = DocumentFieldPath("settle_after")
PAID_AT_FIELD: DocumentFieldPath = DocumentFieldPath("paid_at")
REQUESTED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("requested_at")
CURRENCY_CODE_FIELD: DocumentFieldPath = DocumentFieldPath("currency_code")
AMOUNT_FIELD: DocumentFieldPath = DocumentFieldPath("amount_minor")


class DepositSettingsRepository(
    BusinessScopedRepository[DepositSettingsDocument],
    DepositSettingsRepoContract,
):
    """One settings document per business, keyed by the derived id."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> DepositSettingsDocument | None:
        return self._load(business_id, str(deposit_settings_id_of(business_id)))

    def save(self, settings: DepositSettingsDocument) -> None:
        self._store(str(settings.id), settings)

    def update(
        self, business_id: BusinessId, change: DepositSettingsChange
    ) -> DepositSettingsDocument | None:
        return self._modify_in_business(
            business_id, str(deposit_settings_id_of(business_id)), change
        )


class DepositRequestRepository(
    BusinessScopedRepository[DepositRequestDocument],
    DepositRequestRepoContract,
):
    """
    The deposits asked, read by business and id, by booking or banquet
    request (indexed, migration 1190) and, across businesses for the
    minute's sweep, by status with the end of a hold, a reminder's time or
    the settling after a cancellation; the reports sum them by state and
    currency in the database.
    """

    def save(self, request: DepositRequestDocument) -> None:
        self._store(str(request.id), request)

    def get(
        self, business_id: BusinessId, request_id: DepositRequestId
    ) -> DepositRequestDocument | None:
        return self._load(business_id, str(request_id))

    def update(
        self,
        business_id: BusinessId,
        request_id: DepositRequestId,
        change: DepositRequestChange,
    ) -> DepositRequestDocument | None:
        return self._modify_in_business(business_id, str(request_id), change)

    def list_of_booking(
        self, business_id: BusinessId, booking_id: BookingId
    ) -> list[DepositRequestDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(BOOKING_ID_FIELD, booking_id)],
            order=ascending(REQUESTED_AT_FIELD),
        )

    def list_of_lead(
        self, business_id: BusinessId, lead_id: LeadId
    ) -> list[DepositRequestDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(LEAD_ID_FIELD, lead_id)],
            order=ascending(REQUESTED_AT_FIELD),
        )

    def list_lapsed_holds(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        return self._list_awaiting_until(HOLD_EXPIRES_AT_FIELD, now, limit)

    def list_due_reminders(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        return self._list_awaiting_until(REMINDER_DUE_AT_FIELD, now, limit)

    def list_due_settlements(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        return self._collection.list_by_range(
            time_range(SETTLE_AFTER_FIELD, ending_before=Microseconds(int(now) + 1)),
            (),
            limit=limit,
        )

    def sum_paid(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[DepositSumRow]:
        return self._sum_in_period(business_id, PAID_AT_FIELD, start, end)

    def sum_requested(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[DepositSumRow]:
        return self._sum_in_period(business_id, REQUESTED_AT_FIELD, start, end)

    def _list_awaiting_until(
        self, field: DocumentFieldPath, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        return self._collection.list_by_range(
            time_range(field, ending_before=Microseconds(int(now) + 1)),
            (field_equals(STATUS_FIELD, DepositStatus.AWAITING),),
            limit=limit,
        )

    def _sum_in_period(
        self,
        business_id: BusinessId,
        field: DocumentFieldPath,
        start: Microseconds,
        end: Microseconds,
    ) -> list[DepositSumRow]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    excluding=(without_sandbox(),),
                    ranges=(time_range(field, starting_at=start, ending_before=end),),
                ),
                group_by=(STATUS_FIELD, CURRENCY_CODE_FIELD),
                totals_of=(AMOUNT_FIELD,),
            ),
        )
        return [
            DepositSumRow(
                status=status,
                currency_code=CurrencyCode(group.values[1]),
                count=DepositRequestCount(int(group.count)),
                total_minor=DepositTotalMinor(int(group.totals[0])),
            )
            for group in groups
            if (status := parse_choice(DepositStatus, group.values[0])) is not None
            and group.values[1] is not None
        ]
