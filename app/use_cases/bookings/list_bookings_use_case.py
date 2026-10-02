from datetime import date
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
from app.schemas.dto.operations.bookings import BookingPage, ListBookingsQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.bookings.operations_support import (
    build_audit_entry,
    require_business,
)
from app.utilities.paging.cursor_paging import take_page
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    parse_local_date,
    to_local_moment,
)

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class ListBookingsUseCase(UseCaseContract[ListBookingsQuery, BookingPage]):
    """
    One page of the bookings for the cabinet (concept /bookings), filtered by
    local start date range, status, resource and sandbox, ordered by start
    time (earliest first for upcoming lists, latest first for past ones).
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
        contacts: dict[ContactId, ContactDocument] = {
            contact.id: contact
            for contact in self._contact_repo.list_by_business(business.id)
        }
        matching: list[BookingDocument] = [
            booking
            for booking in self._booking_repo.list_by_business(business.id)
            if self._matches(booking, input_data, zone, date_from, date_to)
        ]
        is_latest_first: bool = input_data.order is BookingOrder.LATEST_FIRST
        bookings: list[BookingDocument]
        next_cursor: PageCursor | None
        bookings, next_cursor = take_page(
            matching,
            input_data.page,
            sort_key=lambda booking: (
                int(booking.starts_at) if is_latest_first else -int(booking.starts_at)
            ),
            item_id=lambda booking: str(booking.id),
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

    def _matches(
        self,
        booking: BookingDocument,
        query: ListBookingsQuery,
        zone: ZoneInfo,
        date_from: date | None,
        date_to: date | None,
    ) -> bool:
        if booking.is_sandbox and not query.include_sandbox:
            return False

        if query.status is not None and booking.status is not query.status:
            return False

        if query.resource_id is not None and booking.resource_id != query.resource_id:
            return False

        local_start: date = to_local_moment(int(booking.starts_at), zone).date()
        if date_from is not None and local_start < date_from:
            return False

        return date_to is None or local_start <= date_to
