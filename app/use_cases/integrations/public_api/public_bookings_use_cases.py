"""The public API's bookings: `GET /v1/public-api/bookings[/{id}]`."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import PublicRecordReaderContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingOrder
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.listing_filters import BookingListFilter
from app.schemas.dto.public_api.access import PublicBookingQuery, PublicListQuery
from app.schemas.dto.public_api.pages import PublicBookingPage
from app.schemas.dto.public_api.records import PublicBooking
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.integrations.api_key_records import require_scope
from app.use_cases.integrations.public_api.public_access import (
    API_BOOKING_ENTITY,
    key_business,
    record_public_read,
)
from app.utilities.paging.keyset_paging import (
    finish_page,
    read_slice,
    single_value_position,
)

UNKNOWN_BOOKING_MESSAGE: str = "Booking not found."


class ListPublicBookingsUseCase(UseCaseContract[PublicListQuery, PublicBookingPage]):
    """
    The key's business's bookings, the latest start first, one keyset page
    at a time (test bookings left out), each with its customer, resource,
    service, value and source. Needs `bookings:read`; audited with the
    number of bookings read.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicListQuery) -> PublicBookingPage:
        require_scope(input_data.principal, ApiKeyScope.BOOKINGS_READ)
        business = key_business(self._business_repo, input_data.principal)
        bookings, next_cursor = finish_page(
            self._booking_repo.page_by_business(
                business.id,
                read_slice(input_data.page, single_value_position),
                BookingListFilter(order=BookingOrder.LATEST_FIRST),
            ),
            input_data.page,
            lambda booking: int(booking.starts_at),
            lambda booking: str(booking.id),
        )
        items = self._record_reader.bookings(business, bookings)
        record_public_read(
            self._audit_log_repo,
            input_data.principal,
            API_BOOKING_ENTITY,
            len(items),
            self._wall_clock.now_unix(),
        )
        return PublicBookingPage(items=items, next_cursor=next_cursor)


class GetPublicBookingUseCase(UseCaseContract[PublicBookingQuery, PublicBooking]):
    """
    One booking of the key's business (404 for another business's or a
    test one). Needs `bookings:read`; audited unless it is the answer of
    the booking the key has just made (`is_audited` False).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        is_audited: bool = True,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._is_audited: bool = is_audited

    def run(self, input_data: PublicBookingQuery) -> PublicBooking:
        if self._is_audited:
            require_scope(input_data.principal, ApiKeyScope.BOOKINGS_READ)
        business = key_business(self._business_repo, input_data.principal)
        booking = self._record_reader.booking(business, input_data.booking_id)
        if booking is None:
            raise NotFoundError(UNKNOWN_BOOKING_MESSAGE)

        if self._is_audited:
            record_public_read(
                self._audit_log_repo,
                input_data.principal,
                API_BOOKING_ENTITY,
                1,
                self._wall_clock.now_unix(),
            )
        return booking
