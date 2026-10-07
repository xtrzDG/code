"""A booking made by staff while a cabinet listens: the live stream scenario."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import LiveEventBusAdapterContract
from app.facilitators.events.event_publisher_facilitator import (
    EventPublisherFacilitator,
)
from app.schemas.dto.bookings import BookingResult
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.contacts.strings import ContactName
from tests.live_events.live_api import LiveApi, parse_stream


def publish_changes_on(api: LiveApi, bus: LiveEventBusAdapterContract) -> None:
    """The world's use cases publish on `bus` (another process's, or the same)."""

    clock: WallClock[Microseconds] = api.world.clock.wall_clock
    api.world.live_events.forward_to = EventPublisherFacilitator(bus, clock)


def book_while_listening(api: LiveApi) -> tuple[list[str], BookingResult]:
    """Stream names and the booking staff made while the stream was open."""

    api.world.add_profile(api.business)
    api.world.add_resource(api.business, "Table 4")
    made: list[BookingResult] = []

    def book() -> None:
        made.append(
            api.world.create_manual_booking().run(
                ManualBookingCommand(
                    business_id=api.business.id,
                    actor_id=api.staff_id,
                    contact_name=ContactName("Walk-in guest"),
                    date=LocalDate("2026-10-07"),
                    time=LocalTimeOfDay("19:00"),
                    party_size=PartySize(2),
                )
            )
        )

    response = api.stream(meanwhile=book)
    assert response.status_code == 200
    messages = parse_stream(response.text)
    names = [message.event for message in messages]
    booking_ids = [message.data.get("ids") for message in messages[1:]]
    assert booking_ids == [[str(made[0].booking.id)]]
    return names, made[0]
