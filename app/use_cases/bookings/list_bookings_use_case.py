from datetime import date, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingOrder
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.listing_filters import BookingListFilter
from app.schemas.dto.operations.bookings import BookingPage, ListBookingsQuery
from app.schemas.dto.paging import KeysetPosition
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.operations_support import (
    build_audit_entry,
)
from app.utilities.paging.keyset_paging import (
    finish_page,
    read_slice,
    single_value_position,
)
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    microseconds_to_seconds,
    parse_local_date,
)

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class ListBookingsUseCase(UseCaseContract[ListBookingsQuery, BookingPage]):
    """
    One page of the bookings for the cabinet (concept /bookings), filtered by
    local start date range, status, resource and sandbox, ordered by start
    time (earliest first for upcoming lists, latest first for past ones):
    a keyset page the database reads, with only its contacts loaded.
    Shows customers' names and phones, so every call is written to the audit
    log as a view by the staff member.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ListBookingsQuery) -> BookingPage:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        date_from: date | None = (
            None
            if input_data.date_from is None
            else parse_local_date(input_data.date_from)
        )
        date_to: date | None = (
            None if input_data.date_to is None else parse_local_date(input_data.date_to)
        )
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationFailedError("The start date is after the end date.")

        resources: dict[ResourceId, ResourceDocument] = {
            resource.id: resource
            for resource in self._resource_repo.list_by_business(business.id)
        }
        is_latest_first: bool = input_data.order is BookingOrder.LATEST_FIRST
        bookings: list[BookingDocument]
        next_cursor: PageCursor | None
        bookings, next_cursor = finish_page(
            self._booking_repo.page_by_business(
                business.id,
                read_slice(
                    input_data.page,
                    single_value_position if is_latest_first else earliest_position,
                ),
                BookingListFilter(
                    starts_from=day_start_seconds(date_from, zone),
                    starts_before=day_start_seconds(
                        None if date_to is None else date_to + timedelta(days=1), zone
                    ),
                    status=input_data.status,
                    resource_id=input_data.resource_id,
                    include_sandbox=input_data.include_sandbox,
                    order=input_data.order,
                ),
            ),
            input_data.page,
            # Earliest-first cursors carry the negated start, as they always did.
            sort_key=lambda booking: (
                int(booking.starts_at) if is_latest_first else -int(booking.starts_at)
            ),
            item_id=lambda booking: str(booking.id),
        )
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, [booking.contact_id for booking in bookings]
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.actor_id,
                AuditAction.VIEW,
                BOOKING_ENTITY,
                None,
                now,
            )
        )
        return BookingPage(
            items=[
                build_booking_view(
                    booking,
                    business.timezone,
                    zone,
                    resources.get(booking.resource_id),
                    contacts.get(booking.contact_id),
                )
                for booking in bookings
            ],
            next_cursor=next_cursor,
        )


def earliest_position(negated_start: int, item_id: str) -> KeysetPosition:
    """The position of an earliest-first cursor (its key is the negated start)."""

    return single_value_position(-negated_start, item_id)


def day_start_seconds(
    local_date: date | None, zone: ZoneInfo
) -> BookingSearchBoundSeconds | None:
    """UTC seconds when the local date begins (None without a date)."""

    if local_date is None:
        return None

    return BookingSearchBoundSeconds(
        max(microseconds_to_seconds(local_day_start_microseconds(local_date, zone)), 0)
    )
