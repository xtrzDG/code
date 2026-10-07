from datetime import timedelta

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.booking_grid import BookingGrid, BookingGridQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    load_scheduling_inputs,
)
from app.use_cases.bookings.calendar.grid_days import GridHours, grid_day
from app.use_cases.bookings.calendar.grid_places import (
    booking_views,
    by_place,
    grid_place,
    shown_places,
)
from app.use_cases.bookings.calendar.grid_window import (
    WindowBookings,
    WindowBounds,
    read_window_bookings,
    window_bounds,
)
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.scheduling.zoned_time import parse_local_date, to_local_date

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class GetBookingGridUseCase(UseCaseContract[BookingGridQuery, BookingGrid]):
    """
    The bookings calendar of the cabinet (Bookings → Day, Week, Nights) in
    one call: every place with its opening hours and how full it is on each
    day of the window, and the bookings that fall in it (none cancelled),
    read by indexed start and end ranges (`grid_window`).

    A place booked by time slots counts the unit-minutes its bookings fill
    within its opening hours; a place booked by the night counts its rooms
    taken each night. Inactive places show only while they keep bookings.
    With the bookings, customers' names are shown, so the call is written
    to the audit log as a view by the staff member; the counts alone (the
    week's heatmap) are not.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BookingGridQuery) -> BookingGrid:
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
        )
        bounds: WindowBounds = window_bounds(
            parse_local_date(input_data.date_from), input_data.days, inputs.zone
        )
        window: WindowBookings = read_window_bookings(
            self._booking_repo,
            inputs.business.id,
            bounds,
            input_data.include_sandbox,
        )
        places: list[ResourceDocument] = shown_places(inputs.resources, window.bookings)
        hours = GridHours(inputs.zone, inputs.business_hours, inputs.exceptions)
        grouped = by_place(window.bookings)
        grid = BookingGrid(
            date_from=input_data.date_from,
            date_to=to_local_date(
                bounds.days[0] + timedelta(days=len(bounds.days) - 1)
            ),
            timezone=inputs.business.timezone,
            places=[grid_place(place) for place in places],
            days=[grid_day(day, places, grouped, hours) for day in bounds.days],
            is_truncated=window.is_truncated,
        )
        if not input_data.include_bookings:
            return grid

        self._audit_log_repo.append(
            build_audit_entry(
                inputs.business.id,
                input_data.actor_id,
                AuditAction.VIEW,
                BOOKING_ENTITY,
                None,
                self._wall_clock.now_unix(),
                input_data.client_ip_address,
            )
        )
        return grid.model_copy(
            update={
                "bookings": booking_views(
                    self._contact_repo,
                    self._knowledge_item_repo,
                    inputs.business.id,
                    inputs.business.timezone,
                    inputs.zone,
                    inputs.resources,
                    window.bookings,
                )
            }
        )
