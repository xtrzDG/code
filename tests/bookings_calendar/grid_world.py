"""
A Tbilisi restaurant (and a guest house) for the bookings calendar: two
tables, a hall open only in the evening, and the grid and move commands.
Now is Monday 2026-10-05, 12:00 in Tbilisi.
"""

from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.booking_grid import BookingGrid, BookingGridQuery
from app.schemas.dto.bookings import BookingResult, RescheduleBookingCommand
from app.schemas.typings.bookings.constrained_integers import BookingGridDayCount
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.bookings.calendar.get_booking_grid_use_case import (
    GetBookingGridUseCase,
)
from tests.operations.builders import every_day
from tests.operations.operations_world import OperationsWorld

TBILISI = "+04:00"


class GridWorld:
    def __init__(self, hours: tuple[str, str] = ("12:00", "23:00")) -> None:
        self.world = OperationsWorld()
        self.staff_id = UserId()
        self.business = self.world.add_business(staff_ids=(self.staff_id,))
        self.world.add_profile(self.business, hours=every_day(*hours))
        self.window = self.world.add_resource(self.business, "Window table", capacity=2)
        self.terrace = self.world.add_resource(
            self.business, "Terrace", capacity=4, unit_count=3
        )
        self.hall = self.world.add_resource(
            self.business, "Hall", capacity=40, schedule=every_day("18:00", "23:00")
        )
        self.guest = self.world.add_contact(self.business, "Nino", "+995555123456")

    def book(
        self,
        place: ResourceDocument,
        starts: str,
        ends: str,
        status: BookingStatus = BookingStatus.CONFIRMED,
        is_sandbox: bool = False,
        party_size: int = 2,
    ) -> BookingDocument:
        """A booking between two Tbilisi wall times ("2026-10-06T19:00")."""

        return self.world.add_booking(
            self.business,
            place,
            self.guest,
            f"{starts}:00{TBILISI}",
            f"{ends}:00{TBILISI}",
            status=status,
            is_sandbox=is_sandbox,
            party_size=party_size,
        )

    def use_case(self) -> GetBookingGridUseCase:
        world = self.world
        return GetBookingGridUseCase(
            business_repo=world.business_repo,
            business_profile_repo=world.profile_repo,
            resource_repo=world.resource_repo,
            schedule_exception_repo=world.exception_repo,
            booking_repo=world.booking_repo,
            knowledge_item_repo=world.knowledge_repo,
            contact_repo=world.contact_repo,
            audit_log_repo=world.audit_repo,
            wall_clock=world.clock.wall_clock,
        )

    def grid(
        self,
        date: str = "2026-10-06",
        days: int = 1,
        include_sandbox: bool = False,
        include_bookings: bool = True,
    ) -> BookingGrid:
        return self.use_case().run(
            BookingGridQuery(
                business_id=self.business.id,
                actor_id=self.staff_id,
                client_ip_address=ClientIpAddress("203.0.113.7"),
                date_from=LocalDate(date),
                days=BookingGridDayCount(days),
                include_sandbox=include_sandbox,
                include_bookings=include_bookings,
            )
        )

    def move(
        self,
        booking: BookingDocument,
        date: str,
        time: str | None,
        place: ResourceId | None = None,
        expected: tuple[str, str | None] | None = None,
    ) -> BookingResult:
        """Drag `booking` to `place` at `date` `time`, from the start `expected`."""

        return self.world.reschedule_booking().run(
            RescheduleBookingCommand(
                business_id=self.business.id,
                booking_id=booking.id,
                new_date=LocalDate(date),
                new_time=None if time is None else LocalTimeOfDay(time),
                language=LanguageTag("en"),
                resource_id=place,
                expected_date=None if expected is None else LocalDate(expected[0]),
                expected_time=(
                    None
                    if expected is None or expected[1] is None
                    else LocalTimeOfDay(expected[1])
                ),
            )
        )


class GuestHouseGrid(GridWorld):
    """Two Deluxe rooms (one resource of two units) and a Standard room."""

    def __init__(self) -> None:
        super().__init__()
        self.deluxe = self.world.add_resource(
            self.business,
            "Deluxe",
            capacity=2,
            unit_count=2,
            kind=ResourceKind.ROOM,
            booking_unit=BookingUnit.NIGHT,
        )
        self.standard = self.world.add_resource(
            self.business,
            "Standard",
            capacity=2,
            kind=ResourceKind.ROOM,
            booking_unit=BookingUnit.NIGHT,
        )
