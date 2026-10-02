import threading
from datetime import datetime

import pytest

from app.facilitators.staff.manager_broadcast_facilitator import (
    ManagerBroadcastFacilitator,
)
from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import BookingResult, CreateBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.scheduling.localized_formatting import (
    FIRST_STRONG_ISOLATE,
    POP_DIRECTIONAL_ISOLATE,
)
from tests.operations.builders import every_day, manager
from tests.operations.fakes import RecordingManagerNotifier
from tests.operations.operations_world import OperationsWorld


def seconds(text: str) -> int:
    return int(datetime.fromisoformat(text).timestamp())


class Restaurant:
    def __init__(self, world: OperationsWorld | None = None) -> None:
        self.world = world or OperationsWorld()
        self.business: BusinessDocument = self.world.add_business()
        self.world.add_profile(self.business)
        self.world.add_resource(self.business, "Table 2", capacity=2)
        self.table_for_four = self.world.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.world.add_resource(self.business, "Table 8", capacity=8)
        self.contact: ContactDocument = self.world.add_contact(self.business)

    def command(
        self,
        time: str | None = "19:00",
        day: str = "2026-10-06",
        party_size: int = 4,
        language: str = "ka",
        is_sandbox: bool = False,
        contact_id: ContactId | None = None,
        name: str = "Giorgi Beridze",
        phone: str | None = "+995555123456",
    ) -> CreateBookingCommand:
        return CreateBookingCommand(
            business_id=self.business.id,
            contact_id=contact_id or self.contact.id,
            conversation_id=ConversationId(),
            contact_name=ContactName(name),
            contact_phone_number=None if phone is None else E164PhoneNumber(phone),
            date=LocalDate(day),
            time=None if time is None else LocalTimeOfDay(time),
            party_size=PartySize(party_size),
            notes=BookingNote("Window seat"),
            source_channel=ChannelKind.WHATSAPP,
            language=LanguageTag(language),
            is_sandbox=is_sandbox,
        )

    def book(self, command: CreateBookingCommand) -> BookingResult:
        return self.world.create_booking().run(command)


def test_booking_is_confirmed_with_a_georgian_confirmation() -> None:
    restaurant = Restaurant()

    result = restaurant.book(restaurant.command())

    view = result.booking
    assert view.status is BookingStatus.CONFIRMED
    assert view.resource_name == "Table 4"
    assert (view.date, view.time, view.end_date, view.end_time) == (
        "2026-10-06",
        "19:00",
        "2026-10-06",
        "21:00",
    )
    assert view.timezone == "Asia/Tbilisi"
    assert view.contact_name == "Giorgi Beridze"
    assert view.contact_phone_number == "+995555123456"
    stored = restaurant.world.bookings_of(restaurant.business.id)
    assert len(stored) == 1
    assert int(stored[0].starts_at) == seconds("2026-10-06T19:00:00+04:00")
    assert int(stored[0].ends_at) == seconds("2026-10-06T21:00:00+04:00")
    assert stored[0].notes == "Window seat"
    text = str(result.confirmation_text)
    assert "დადასტურებულია" in text
    assert "ოქტომბერი" in text
    assert "19:00" in text and "Giorgi Beridze" in text and ": 4." in text


def test_contact_details_are_updated_and_audited() -> None:
    restaurant = Restaurant()

    restaurant.book(restaurant.command())

    contact = restaurant.world.contact_repo.get(
        restaurant.business.id, restaurant.contact.id
    )
    assert contact is not None
    assert (contact.name, contact.phone_number) == ("Giorgi Beridze", "+995555123456")
    entries = restaurant.world.audit_repo.list_by_business(restaurant.business.id)
    assert [(entry.action, entry.entity, entry.actor_id) for entry in entries] == [
        (AuditAction.UPDATE, "contact", None)
    ]


def test_every_manager_is_notified_in_their_language() -> None:
    restaurant = Restaurant()

    restaurant.book(restaurant.command())

    texts = {
        str(contact.language): str(text)
        for contact, text in restaurant.world.notifier.sent
    }
    assert set(texts) == {"ka", "ru", "en"}
    assert texts["ka"].startswith("ახალი ჯავშანი · Salobie Bia")
    assert texts["ru"].startswith("Новая бронь · Salobie Bia")
    assert "Телефон: +995 555 12 34 56" in texts["ru"]
    assert "Пожелания: Window seat" in texts["ru"]
    assert "Channel: WhatsApp" in texts["en"]
    assert "Table 4" in texts["en"] and "19:00–21:00" in texts["en"]
    assert "October 6, 2026" in texts["en"]
    assert restaurant.world.calendar_sync.synced[0].id == (
        restaurant.world.bookings_of(restaurant.business.id)[0].id
    )


def test_sandbox_booking_notifies_nobody_and_skips_the_calendar() -> None:
    restaurant = Restaurant()

    result = restaurant.book(restaurant.command(is_sandbox=True))

    assert result.booking.is_sandbox
    assert restaurant.world.notifier.sent == []
    assert restaurant.world.calendar_sync.synced == []


def test_failing_notifier_never_breaks_the_booking() -> None:
    world = OperationsWorld()
    world.notifier = RecordingManagerNotifier(
        failing_addresses=frozenset({"+995555000111"}),
        raising_addresses=frozenset({"4242"}),
    )
    world.broadcaster = ManagerBroadcastFacilitator(world.notifier)
    restaurant = Restaurant(world)

    result = restaurant.book(restaurant.command())

    assert result.booking.status is BookingStatus.CONFIRMED
    assert [str(contact.address) for contact, _ in world.notifier.sent] == [
        "+995555000111",
        "anna@example.com",
    ]


def test_taken_last_unit_raises_conflict() -> None:
    restaurant = Restaurant()
    restaurant.book(restaurant.command(party_size=6))

    with pytest.raises(ConflictError, match="already booked"):
        restaurant.book(restaurant.command(party_size=6))

    # A smaller party still gets a smaller table at the same time.
    assert restaurant.book(restaurant.command(party_size=2)).booking.resource_name == (
        "Table 2"
    )


def test_concurrent_requests_for_the_last_unit_book_it_once() -> None:
    restaurant = Restaurant()
    use_case = restaurant.world.create_booking()
    barrier = threading.Barrier(8)
    outcomes: list[str] = []
    outcomes_lock = threading.Lock()

    def attempt() -> None:
        barrier.wait()
        try:
            use_case.run(restaurant.command(party_size=8, language="en"))
            outcome = "booked"
        except ConflictError:
            outcome = "conflict"

        with outcomes_lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["booked"] + ["conflict"] * 7
    assert len(restaurant.world.bookings_of(restaurant.business.id)) == 1


@pytest.mark.parametrize(
    ("time", "day", "message"),
    [
        ("23:30", "2026-10-06", "closed"),
        ("11:00", "2026-10-06", "closed"),
        ("12:30", "2026-10-05", "too soon"),
        (None, "2026-10-06", "time is required"),
    ],
)
def test_invalid_times_are_refused(time: str | None, day: str, message: str) -> None:
    restaurant = Restaurant()

    with pytest.raises(ValidationFailedError, match=message):
        restaurant.book(restaurant.command(time=time, day=day))

    assert restaurant.world.bookings_of(restaurant.business.id) == []


def test_party_limits_and_unknown_contact() -> None:
    restaurant = Restaurant()

    with pytest.raises(ValidationFailedError, match="12 guests"):
        restaurant.book(restaurant.command(party_size=20))

    with pytest.raises(ValidationFailedError, match="No bookable resource"):
        restaurant.book(restaurant.command(party_size=10))

    with pytest.raises(NotFoundError):
        restaurant.book(restaurant.command(contact_id=ContactId()))


def test_new_york_booking_in_the_daylight_saving_gap_is_refused() -> None:
    world = OperationsWorld(datetime.fromisoformat("2026-03-01T00:00:00+00:00"))
    diner = world.add_business(
        name="Night Owl Diner",
        country_code="US",
        timezone="America/New_York",
        currency_code="USD",
        languages=("en", "es"),
        owner_language="en",
    )
    world.add_profile(diner, hours=every_day("00:00", "06:00"), slot_minutes=60)
    world.add_resource(diner, "Booth", capacity=4)
    contact = world.add_contact(diner)
    command = CreateBookingCommand(
        business_id=diner.id,
        contact_id=contact.id,
        contact_name=ContactName("Jordan"),
        date=LocalDate("2026-03-08"),
        time=LocalTimeOfDay("02:30"),
        party_size=PartySize(2),
        source_channel=ChannelKind.WEB_CHAT,
        language=LanguageTag("en"),
    )

    with pytest.raises(ValidationFailedError, match="does not exist"):
        world.create_booking().run(command)

    fold = world.create_booking().run(
        command.model_copy(
            update={"date": LocalDate("2026-11-01"), "time": LocalTimeOfDay("01:30")}
        )
    )
    stored = world.bookings_of(diner.id)[0]
    assert int(stored.starts_at) == seconds("2026-11-01T01:30:00-04:00")
    assert fold.booking.time == "01:30"


def test_hotel_stay_is_booked_by_the_night_in_german() -> None:
    world = OperationsWorld()
    hotel = world.add_business(
        name="Hotel Aurora",
        country_code="IT",
        timezone="Europe/Rome",
        currency_code="EUR",
        languages=("it", "en", "de"),
        owner_language="it",
        niche_key=NicheKey.HOTEL,
    )
    world.add_profile(
        hotel,
        resource_kind=ResourceKind.ROOM,
        niche_answers={"check_in_time": "15:00", "check_out_time": "10:00"},
    )
    world.add_resource(
        hotel,
        "Double room",
        capacity=2,
        unit_count=1,
        kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
    )
    contact = world.add_contact(hotel)
    command = CreateBookingCommand(
        business_id=hotel.id,
        contact_id=contact.id,
        contact_name=ContactName("Lena Schmidt"),
        contact_phone_number=E164PhoneNumber("+4915123456789"),
        date=LocalDate("2026-10-12"),
        nights=NightCount(3),
        party_size=PartySize(2),
        source_channel=ChannelKind.TELEGRAM,
        language=LanguageTag("de"),
    )

    result = world.create_booking().run(command)

    stored = world.bookings_of(hotel.id)[0]
    assert int(stored.starts_at) == seconds("2026-10-12T15:00:00+02:00")
    assert int(stored.ends_at) == seconds("2026-10-15T10:00:00+02:00")
    text = str(result.confirmation_text)
    assert "Anreise Montag, 12. Oktober 2026 ab 15:00" in text
    assert "Abreise Donnerstag, 15. Oktober 2026 bis 10:00" in text
    with pytest.raises(ConflictError):
        world.create_booking().run(command.model_copy(update={"nights": NightCount(1)}))


def test_hebrew_confirmation_isolates_latin_values() -> None:
    world = OperationsWorld()
    clinic = world.add_business(
        name="Tel Aviv Smile",
        country_code="IL",
        timezone="Asia/Jerusalem",
        currency_code="ILS",
        languages=("he", "en", "ar"),
        owner_language="he",
        managers=(manager("Dana", ManagerContactChannel.SMS, "+972502345678", "he"),),
    )
    world.add_profile(clinic, hours=every_day("08:00", "20:00"), slot_minutes=30)
    world.add_resource(clinic, "Chair 1", capacity=1)
    contact = world.add_contact(clinic)

    result = world.create_booking().run(
        CreateBookingCommand(
            business_id=clinic.id,
            contact_id=contact.id,
            contact_name=ContactName("Noa Levi"),
            date=LocalDate("2026-10-07"),
            time=LocalTimeOfDay("10:30"),
            party_size=PartySize(1),
            source_channel=ChannelKind.WHATSAPP,
            language=LanguageTag("he"),
        )
    )

    text = str(result.confirmation_text)
    assert "אושרה" in text
    assert f"{FIRST_STRONG_ISOLATE}Noa Levi{POP_DIRECTIONAL_ISOLATE}" in text
    assert f"{FIRST_STRONG_ISOLATE}10:30{POP_DIRECTIONAL_ISOLATE}" in text
    # The manager reads Hebrew, which staff texts do not have yet: English.
    assert str(world.notifier.sent[0][1]).startswith("New booking")


def test_unsupported_language_falls_back_to_english_and_regional_to_base() -> None:
    restaurant = Restaurant()

    portuguese = restaurant.book(restaurant.command(language="pt-BR", time="13:00"))
    russian = restaurant.book(restaurant.command(language="ru-RU", time="16:00"))

    assert str(portuguese.confirmation_text).startswith("Your booking at Salobie Bia")
    assert "October 6, 2026" in str(portuguese.confirmation_text)
    assert str(russian.confirmation_text).startswith("Ваша бронь в «Salobie Bia»")
    assert "6 октября 2026" in str(russian.confirmation_text)
