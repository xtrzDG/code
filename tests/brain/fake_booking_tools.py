"""
In-memory stand-ins for the booking tools: availability, create, cancel,
reschedule. One FakeBookings book serves the three booking commands.
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus, BookingUnit
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    AvailableSlot,
    BookingResult,
    BookingView,
    CancelBookingCommand,
    CreateBookingCommand,
    RescheduleBookingCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import TimezoneName

TABLE_RESOURCE_ID: ResourceId = ResourceId()


class FakeCheckAvailability(UseCaseContract[AvailabilityQuery, AvailabilityResult]):
    def __init__(self, timezone: TimezoneName, free_times: list[str]) -> None:
        self.timezone: TimezoneName = timezone
        self.free_times: list[str] = free_times
        self.queries: list[AvailabilityQuery] = []

    def run(self, input_data: AvailabilityQuery) -> AvailabilityResult:
        self.queries.append(input_data)
        return AvailabilityResult(
            timezone=self.timezone,
            is_open_on_date=True,
            slots=[
                AvailableSlot(
                    resource_id=TABLE_RESOURCE_ID,
                    resource_name=ResourceName("Table by the window"),
                    booking_unit=BookingUnit.TIME_SLOT,
                    date=input_data.date,
                    time=LocalTimeOfDay(free_time),
                )
                for free_time in self.free_times
            ],
        )


@dataclass
class FakeBookings:
    """create, cancel and reschedule over one in-memory list."""

    timezone: TimezoneName
    is_slot_taken: bool = False
    commands: list[object] = field(default_factory=list[object])
    bookings: dict[BookingId, BookingView] = field(
        default_factory=dict[BookingId, BookingView]
    )

    def create(self, command: CreateBookingCommand) -> BookingResult:
        self.commands.append(command)
        if self.is_slot_taken:
            raise ConflictError("This time is already taken; offer another slot.")

        booking = BookingView(
            id=BookingId(),
            business_id=command.business_id,
            resource_id=TABLE_RESOURCE_ID,
            resource_name=ResourceName("Table by the window"),
            contact_id=command.contact_id,
            contact_name=command.contact_name,
            contact_phone_number=command.contact_phone_number,
            date=command.date,
            time=command.time,
            end_date=command.date,
            end_time=None,
            timezone=self.timezone,
            party_size=command.party_size,
            status=BookingStatus.CONFIRMED,
            source_channel=command.source_channel,
            notes=command.notes,
            is_sandbox=command.is_sandbox,
            conversation_id=command.conversation_id,
            language=command.language,
            created_at=Microseconds(1_790_000_000_000_000),
        )
        self.bookings[booking.id] = booking
        return BookingResult(
            booking=booking,
            confirmation_text=MessageText(f"Booked for {command.date} {command.time}."),
        )

    def cancel(self, command: CancelBookingCommand) -> BookingResult:
        self.commands.append(command)
        booking: BookingView | None = (
            None
            if command.booking_id is None
            else self.bookings.get(command.booking_id)
        )
        if booking is None:
            raise NotFoundError("No booking was found for these details.")

        cancelled: BookingView = booking.model_copy(
            update={"status": BookingStatus.CANCELLED}
        )
        self.bookings[booking.id] = cancelled
        return BookingResult(
            booking=cancelled,
            confirmation_text=MessageText("The booking is cancelled."),
        )

    def reschedule(self, command: RescheduleBookingCommand) -> BookingResult:
        self.commands.append(command)
        booking: BookingView | None = (
            None
            if command.booking_id is None
            else self.bookings.get(command.booking_id)
        )
        if booking is None:
            raise NotFoundError("No booking was found for these details.")

        moved: BookingView = booking.model_copy(
            update={
                "date": command.new_date,
                "end_date": command.new_date,
                "time": command.new_time,
            }
        )
        self.bookings[booking.id] = moved
        return BookingResult(
            booking=moved,
            confirmation_text=MessageText(f"Moved to {command.new_date}."),
        )


class FakeCreateBooking(UseCaseContract[CreateBookingCommand, BookingResult]):
    def __init__(self, bookings: FakeBookings) -> None:
        self._bookings: FakeBookings = bookings

    def run(self, input_data: CreateBookingCommand) -> BookingResult:
        return self._bookings.create(input_data)


class FakeCancelBooking(UseCaseContract[CancelBookingCommand, BookingResult]):
    def __init__(self, bookings: FakeBookings) -> None:
        self._bookings: FakeBookings = bookings

    def run(self, input_data: CancelBookingCommand) -> BookingResult:
        return self._bookings.cancel(input_data)


class FakeRescheduleBooking(UseCaseContract[RescheduleBookingCommand, BookingResult]):
    def __init__(self, bookings: FakeBookings) -> None:
        self._bookings: FakeBookings = bookings

    def run(self, input_data: RescheduleBookingCommand) -> BookingResult:
        return self._bookings.reschedule(input_data)
