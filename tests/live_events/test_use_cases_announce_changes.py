"""Each change the cabinet shows is announced once, by id, without sandbox noise."""

from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.bookings import CancelBookingCommand, CreateLeadCommand
from app.schemas.dto.operations.bookings import (
    ManualBookingCommand,
    UpdateBookingCommand,
)
from app.schemas.dto.operations.handoffs import ResolveHandoffCommand
from app.schemas.dto.operations.leads import UpdateLeadStatusCommand
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.bookings.strings import BookingNote, LeadDetails
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from tests.live_events.recording_event_publisher import PublishedLiveEvent
from tests.operations.handoff_fixture import HandoffFixture
from tests.operations.restaurant_booking_fixture import Restaurant

MONDAY_NOON: str = "2026-10-05T09:00:00+00:00"


def test_bookings_are_announced_when_made_moved_or_changed() -> None:
    restaurant = Restaurant()
    events = restaurant.world.live_events
    booking = restaurant.book(restaurant.command()).booking
    restaurant.book(restaurant.command(is_sandbox=True, time="20:00"))

    restaurant.world.update_booking().run(
        UpdateBookingCommand(
            business_id=restaurant.business.id,
            actor_id=UserId(),
            booking_id=booking.id,
            notes=BookingNote("A birthday: bring the cake at 21:00"),
        )
    )
    restaurant.world.cancel_booking().run(
        CancelBookingCommand(
            business_id=restaurant.business.id,
            booking_id=booking.id,
            language=LanguageTag("en"),
        )
    )
    manual = restaurant.world.create_manual_booking().run(
        ManualBookingCommand(
            business_id=restaurant.business.id,
            actor_id=UserId(),
            contact_name=ContactName("Walk-in guest"),
            date=LocalDate("2026-10-07"),
            time=LocalTimeOfDay("19:00"),
            party_size=PartySize(2),
        )
    )

    business_id = restaurant.business.id
    assert events.events == [
        PublishedLiveEvent(
            business_id, LiveEventKind.BOOKING_CREATED, (str(booking.id),)
        ),
        PublishedLiveEvent(
            business_id, LiveEventKind.BOOKING_CHANGED, (str(booking.id),)
        ),
        PublishedLiveEvent(
            business_id, LiveEventKind.BOOKING_CHANGED, (str(booking.id),)
        ),
        PublishedLiveEvent(
            business_id, LiveEventKind.BOOKING_CREATED, (str(manual.booking.id),)
        ),
    ]


def test_a_handoff_is_announced_when_opened_and_once_when_resolved() -> None:
    fixture = HandoffFixture(MONDAY_NOON)
    events = fixture.world.live_events
    handoff = fixture.hand_off()
    fixture.hand_off(is_sandbox=True)

    for _ in range(2):
        fixture.world.resolve_handoff().run(
            ResolveHandoffCommand(
                business_id=fixture.business.id, handoff_id=handoff.id
            )
        )

    subjects = (str(handoff.id), str(fixture.conversation.id))
    assert events.events == [
        PublishedLiveEvent(
            fixture.business.id, LiveEventKind.HANDOFF_CREATED, subjects
        ),
        PublishedLiveEvent(
            fixture.business.id, LiveEventKind.HANDOFF_RESOLVED, subjects
        ),
    ]


def test_requests_are_announced_when_created_and_when_they_move_on() -> None:
    restaurant = Restaurant()
    events = restaurant.world.live_events

    def create(is_sandbox: bool) -> LeadId:
        return (
            restaurant.world.create_lead()
            .run(
                CreateLeadCommand(
                    business_id=restaurant.business.id,
                    contact_id=restaurant.contact.id,
                    lead_type=LeadType.BANQUET,
                    details=LeadDetails("A birthday for 30 guests"),
                    source_channel=ChannelKind.WHATSAPP,
                    language=LanguageTag("en"),
                    is_sandbox=is_sandbox,
                )
            )
            .id
        )

    lead_id, sandbox_lead_id = create(is_sandbox=False), create(is_sandbox=True)
    for changed_id in (lead_id, lead_id, sandbox_lead_id):
        restaurant.world.update_lead_status().run(
            UpdateLeadStatusCommand(
                business_id=restaurant.business.id,
                lead_id=changed_id,
                status=LeadStatus.WON,
            )
        )

    assert events.kinds() == [LiveEventKind.LEAD_CREATED, LiveEventKind.LEAD_CHANGED]
    assert [published.ids for published in events.events] == [
        (str(lead_id),),
        (str(lead_id),),
    ]
