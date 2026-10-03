"""Bookings in other countries and scripts: DST gaps, hotel nights, Hebrew text."""

from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.scheduling.localized_formatting import (
    FIRST_STRONG_ISOLATE,
    POP_DIRECTIONAL_ISOLATE,
)
from tests.operations.builders import every_day, manager, seconds
from tests.operations.operations_world import OperationsWorld


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
